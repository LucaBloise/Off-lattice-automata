#!/usr/bin/env python3
"""
Animate Vicsek simulation trajectories produced by the Java simulation module.

Expected run folder contents:
- trajectory.txt  (columns: t id x y vx vy theta)
- properties.txt  (key=value per line)

Examples:
- python visualization/animate_vicsek.py --run-dir simulation/outputs/run_20260320_101530_123
- python visualization/animate_vicsek.py --outputs-dir simulation/outputs --latest
- python visualization/animate_vicsek.py --outputs-dir simulation/outputs --latest --save animation.mp4 --fps 30
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Animate Vicsek trajectory output.")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Path to a single run directory containing trajectory.txt and properties.txt.",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=None,
        help="Path to outputs directory that contains run_* subfolders.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use latest run directory from outputs-dir (or default outputs path).",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="Frame stride. 1 means every simulation step.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Delay between frames in milliseconds for interactive playback.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="FPS when saving animation.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Optional output animation path. Extension decides writer (.mp4 or .gif).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=120,
        help="DPI used when saving animation.",
    )
    parser.add_argument(
        "--figsize",
        type=float,
        nargs=2,
        default=(8.0, 8.0),
        metavar=("W", "H"),
        help="Figure size in inches.",
    )
    parser.add_argument(
        "--vector-length-scale",
        type=float,
        default=20.0,
        help="Multiplier applied to vx, vy only for visualization.",
    )
    parser.add_argument(
        "--vector-width",
        type=float,
        default=0.00525,
        help="Arrow shaft width in axes units.",
    )
    return parser.parse_args()


def parse_properties(properties_path: Path) -> Dict[str, str]:
    properties: Dict[str, str] = {}
    if not properties_path.exists():
        return properties

    for raw_line in properties_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        properties[key.strip()] = value.strip()

    return properties


def parse_trajectory(trajectory_path: Path) -> np.ndarray:
    if not trajectory_path.exists():
        raise FileNotFoundError(f"trajectory file not found: {trajectory_path}")

    data = np.loadtxt(trajectory_path, skiprows=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)

    if data.shape[1] != 7:
        raise ValueError(
            f"trajectory must have 7 columns (t id x y vx vy theta), got {data.shape[1]}"
        )

    return data


def build_state_arrays(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    t_idx = data[:, 0].astype(np.int64)
    ids = data[:, 1].astype(np.int64)

    n_steps = int(t_idx.max()) + 1
    n_particles = int(ids.max()) + 1

    x = np.zeros((n_steps, n_particles), dtype=np.float64)
    y = np.zeros((n_steps, n_particles), dtype=np.float64)
    vx = np.zeros((n_steps, n_particles), dtype=np.float64)
    vy = np.zeros((n_steps, n_particles), dtype=np.float64)
    theta = np.zeros((n_steps, n_particles), dtype=np.float64)

    x[t_idx, ids] = data[:, 2]
    y[t_idx, ids] = data[:, 3]
    vx[t_idx, ids] = data[:, 4]
    vy[t_idx, ids] = data[:, 5]
    theta[t_idx, ids] = data[:, 6]

    return x, y, vx, vy, theta


def find_default_outputs_dir() -> Path:
    candidates = [
        Path("simulation") / "outputs",
        Path("outputs"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return candidates[0]


def find_latest_run(outputs_dir: Path) -> Path:
    if not outputs_dir.exists() or not outputs_dir.is_dir():
        raise FileNotFoundError(f"outputs directory not found: {outputs_dir}")

    runs = [p for p in outputs_dir.iterdir() if p.is_dir()]
    if not runs:
        raise FileNotFoundError(f"no run directories found in: {outputs_dir}")

    return max(runs, key=lambda p: p.stat().st_mtime)


def resolve_run_dir(args: argparse.Namespace) -> Path:
    if args.run_dir is not None:
        return args.run_dir

    outputs_dir = args.outputs_dir if args.outputs_dir is not None else find_default_outputs_dir()

    if args.latest or args.run_dir is None:
        return find_latest_run(outputs_dir)

    raise ValueError("Could not resolve run directory. Provide --run-dir or --outputs-dir --latest")


def as_float(properties: Dict[str, str], key: str, fallback: float) -> float:
    raw = properties.get(key)
    if raw is None:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def as_int(properties: Dict[str, str], key: str, fallback: int) -> int:
    raw = properties.get(key)
    if raw is None:
        return fallback
    try:
        return int(float(raw))
    except ValueError:
        return fallback


def as_bool(properties: Dict[str, str], key: str, fallback: bool) -> bool:
    raw = properties.get(key)
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "y"}


def main() -> None:
    args = parse_args()

    if args.stride <= 0:
        raise ValueError("--stride must be >= 1")
    if args.vector_length_scale <= 0:
        raise ValueError("--vector-length-scale must be > 0")
    if args.vector_width <= 0:
        raise ValueError("--vector-width must be > 0")

    run_dir = resolve_run_dir(args)
    trajectory_path = run_dir / "trajectory.txt"
    properties_path = run_dir / "properties.txt"

    properties = parse_properties(properties_path)
    trajectory_data = parse_trajectory(trajectory_path)
    x, y, vx, vy, theta = build_state_arrays(trajectory_data)

    n_steps, n_particles = x.shape
    frame_indices = np.arange(0, n_steps, args.stride, dtype=np.int64)

    L = as_float(properties, "L", fallback=max(float(np.max(x)), float(np.max(y)), 10.0))
    eta = properties.get("eta", "unknown")
    density = properties.get("density", "unknown")
    v0 = properties.get("v0", "unknown")
    dt = properties.get("dt", "unknown")
    radius = properties.get("interaction_radius", "unknown")
    scenario = properties.get("scenario", properties.get("model", "unknown"))
    has_leader = as_bool(properties, "has_leader", False)
    leader_id = as_int(properties, "leader_id", -1)
    valid_leader = has_leader and 0 <= leader_id < n_particles

    follower_indices = np.arange(n_particles)
    if valid_leader:
        follower_indices = np.array([idx for idx in range(n_particles) if idx != leader_id], dtype=np.int64)

    fig, ax = plt.subplots(figsize=tuple(args.figsize))
    ax.set_xlim(0.0, L)
    ax.set_ylim(0.0, L)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("Vicsek Off-lattice Animation")

    initial_step = int(frame_indices[0])
    quiver = ax.quiver(
        x[initial_step, follower_indices],
        y[initial_step, follower_indices],
        vx[initial_step, follower_indices] * args.vector_length_scale,
        vy[initial_step, follower_indices] * args.vector_length_scale,
        theta[initial_step, follower_indices],
        cmap="hsv",
        clim=(0.0, 2.0 * math.pi),
        angles="xy",
        scale_units="xy",
        scale=1.0,
        width=args.vector_width,
        headwidth=4.5,
        headlength=6.0,
        headaxislength=5.5,
    )

    leader_quiver = None
    leader_marker = None
    if valid_leader:
        leader_quiver = ax.quiver(
            [x[initial_step, leader_id]],
            [y[initial_step, leader_id]],
            [vx[initial_step, leader_id] * args.vector_length_scale],
            [vy[initial_step, leader_id] * args.vector_length_scale],
            color="#111111",
            angles="xy",
            scale_units="xy",
            scale=1.0,
            width=max(args.vector_width * 1.7, 0.004),
            headwidth=5.5,
            headlength=7.0,
            headaxislength=6.0,
            zorder=5,
        )
        leader_marker = ax.scatter(
            [x[initial_step, leader_id]],
            [y[initial_step, leader_id]],
            s=30,
            c="#ffffff",
            edgecolors="#111111",
            linewidths=1.2,
            zorder=6,
            label="leader",
        )
        ax.legend(loc="lower right", fontsize=8)

    colorbar = fig.colorbar(quiver, ax=ax, pad=0.02)
    colorbar.set_label("velocity angle (rad)")

    info_lines = [
        f"run: {run_dir.name}",
        f"scenario={scenario}",
        f"N={n_particles}  L={L:g}  density={density}",
        f"eta={eta}  v0={v0}  dt={dt}  r={radius}",
    ]
    if valid_leader:
        info_lines.append(f"leader_id={leader_id}")
    info_text = ax.text(
        0.02,
        0.98,
        "\n".join(info_lines),
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8, "edgecolor": "gray"},
    )

    step_text = ax.text(
        0.98,
        0.98,
        "",
        transform=ax.transAxes,
        va="top",
        ha="right",
        fontsize=10,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8, "edgecolor": "gray"},
    )

    def update(frame_number: int):
        step = int(frame_indices[frame_number])
        offsets = np.column_stack((x[step, follower_indices], y[step, follower_indices]))
        quiver.set_offsets(offsets)
        quiver.set_UVC(
            vx[step, follower_indices] * args.vector_length_scale,
            vy[step, follower_indices] * args.vector_length_scale,
            theta[step, follower_indices],
        )
        artists = [quiver, step_text, info_text]

        if valid_leader and leader_quiver is not None and leader_marker is not None:
            leader_offsets = np.array([[x[step, leader_id], y[step, leader_id]]])
            leader_quiver.set_offsets(leader_offsets)
            leader_quiver.set_UVC(
                np.array([vx[step, leader_id] * args.vector_length_scale]),
                np.array([vy[step, leader_id] * args.vector_length_scale]),
            )
            leader_marker.set_offsets(leader_offsets)
            artists.extend([leader_quiver, leader_marker])

        step_text.set_text(f"step={step} / {n_steps - 1}")
        return tuple(artists)

    animation = FuncAnimation(
        fig,
        update,
        frames=len(frame_indices),
        interval=args.interval,
        blit=False,
        repeat=True,
    )

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        suffix = args.save.suffix.lower()
        if suffix == ".gif":
            animation.save(args.save, writer="pillow", fps=args.fps, dpi=args.dpi)
        else:
            animation.save(args.save, fps=args.fps, dpi=args.dpi)
        print(f"Saved animation: {args.save.resolve()}")
    else:
        plt.show()


if __name__ == "__main__":
    main()

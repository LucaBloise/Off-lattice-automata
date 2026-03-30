#!/usr/bin/env python3
"""
Post-processing for optional leader alignment analysis.

Given one simulation run, computes:
- theta_S(t) = atan2(<sin(theta_i(t))>, <cos(theta_i(t))>) over all particles i excluding leader
- C(t) = cos(theta_L(t) - theta_S(t))

Input files expected in run directory:
- trajectory.txt with columns: t id x y vx vy theta
- properties.txt with metadata including has_leader and leader_id

Examples:
- python visualization/plot_leader_correlation.py --run-dir simulation/outputs/run_20260325_120000_000
- python visualization/plot_leader_correlation.py --outputs-dir simulation/outputs --latest
- python visualization/plot_leader_correlation.py --outputs-dir simulation/outputs --latest --save visualization/leader_corr.png
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot theta_S(t) and C(t) for one run.")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Path to one run directory containing trajectory.txt and properties.txt.",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=None,
        help="Path to outputs directory containing run folders.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use latest run in outputs-dir (or default outputs path).",
    )
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Optional path to save figure (png/pdf/svg). If omitted, opens interactive window.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=140,
        help="DPI for saved figure.",
    )
    return parser.parse_args()


def parse_properties(path: Path) -> Dict[str, str]:
    props: Dict[str, str] = {}
    if not path.exists():
        return props

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        props[k.strip()] = v.strip()
    return props


def as_int(props: Dict[str, str], key: str, default: int) -> int:
    value = props.get(key)
    if value is None:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def as_bool(props: Dict[str, str], key: str, default: bool) -> bool:
    value = props.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def parse_trajectory(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Missing trajectory file: {path}")

    data = np.loadtxt(path, skiprows=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] != 7:
        raise ValueError(f"Expected 7 columns in trajectory, got {data.shape[1]}")
    return data


def build_theta_array(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    t = data[:, 0].astype(np.int64)
    ids = data[:, 1].astype(np.int64)
    theta_values = data[:, 6]

    n_steps = int(t.max()) + 1
    n_particles = int(ids.max()) + 1

    theta = np.zeros((n_steps, n_particles), dtype=np.float64)
    theta[t, ids] = theta_values

    t_axis = np.arange(n_steps, dtype=np.int64)
    return t_axis, theta


def default_outputs_dir() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [repo_root / "simulation" / "outputs", repo_root / "outputs"]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return candidates[1]


def find_latest_run(outputs_dir: Path) -> Path:
    if not outputs_dir.exists() or not outputs_dir.is_dir():
        raise FileNotFoundError(f"outputs directory does not exist: {outputs_dir}")

    run_dirs = []
    for trajectory in outputs_dir.rglob("trajectory.txt"):
        run_dir = trajectory.parent
        if (run_dir / "properties.txt").exists():
            run_dirs.append(run_dir)

    if not run_dirs:
        raise FileNotFoundError(f"No runs found in: {outputs_dir}")

    run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return run_dirs[0]


def resolve_run_dir(args: argparse.Namespace) -> Path:
    if args.run_dir is not None:
        return args.run_dir

    outputs_dir = args.outputs_dir if args.outputs_dir is not None else default_outputs_dir()
    if args.latest or args.run_dir is None:
        return find_latest_run(outputs_dir)

    raise ValueError("Could not resolve run directory")


def circular_mean(theta_matrix: np.ndarray, axis: int) -> np.ndarray:
    return np.arctan2(np.mean(np.sin(theta_matrix), axis=axis), np.mean(np.cos(theta_matrix), axis=axis))


def main() -> None:
    args = parse_args()

    run_dir = resolve_run_dir(args)
    props = parse_properties(run_dir / "properties.txt")

    has_leader = as_bool(props, "has_leader", False)
    leader_id = as_int(props, "leader_id", -1)

    data = parse_trajectory(run_dir / "trajectory.txt")
    t_axis, theta = build_theta_array(data)

    n_particles = theta.shape[1]
    if has_leader and leader_id >= n_particles:
        raise ValueError(f"leader_id={leader_id} is out of range for n_particles={n_particles}")

    if has_leader and leader_id >= 0:
        follower_ids = np.array([idx for idx in range(n_particles) if idx != leader_id], dtype=np.int64)
    else:
        follower_ids = np.arange(n_particles, dtype=np.int64)

    if len(follower_ids) == 0:
        raise ValueError("No follower particles available to compute theta_S(t)")

    theta_s = circular_mean(theta[:, follower_ids], axis=1)

    scenario = props.get("scenario", props.get("model", "unknown"))
    eta = props.get("eta", "?")

    if has_leader and leader_id >= 0:
        theta_l = theta[:, leader_id]
        c_t = np.cos(theta_l - theta_s)

        fig, axes = plt.subplots(2, 1, figsize=(10.0, 7.0), sharex=True)

        axes[0].plot(t_axis, theta_s, color="#1f77b4", linewidth=1.5, label="theta_S(t) collective")
        axes[0].set_ylabel("Ángulo promedio\ncolectivo (rad)", fontsize=16)
        axes[0].tick_params(axis="both", which="major", labelsize=16)
        axes[0].grid(alpha=0.25)

        axes[1].plot(t_axis, c_t, color="#2ca02c", linewidth=1.6, label="C(t)=cos(theta_L-theta_S)")
        axes[1].axhline(0.0, color="black", linewidth=0.8, alpha=0.4)
        axes[1].set_xlabel(r"Tiempo de simulación ($t$)", fontsize=16)
        axes[1].set_ylabel("Correlación angular", fontsize=16)
        axes[1].set_ylim(-1.05, 1.05)
        axes[1].tick_params(axis="both", which="major", labelsize=16)
        axes[1].grid(alpha=0.25)
    else:
        fig, ax = plt.subplots(1, 1, figsize=(10.0, 4.2))
        ax.plot(t_axis, theta_s, color="#1f77b4", linewidth=1.5, label="theta_S(t) collective")
        ax.set_xlabel(r"Tiempo de simulación ($t$)", fontsize=16)
        ax.set_ylabel("Ángulo promedio colectivo (rad)", fontsize=16)
        ax.tick_params(axis="both", which="major", labelsize=16)
        ax.grid(alpha=0.25)

    fig.tight_layout()

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=args.dpi)
        print(f"Saved figure: {args.save.resolve()}")
    else:
        plt.show()


if __name__ == "__main__":
    main()

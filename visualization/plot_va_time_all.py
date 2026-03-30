#!/usr/bin/env python3
"""
Plot Va(t) for all runs in one folder on a single figure.

Each run contributes one line and is identified in the legend.

Examples:
- python visualization/plot_va_time_all.py --outputs-dir simulation/outputs
- python visualization/plot_va_time_all.py --outputs-dir simulation/outputs --latest-count 20
- python visualization/plot_va_time_all.py --outputs-dir simulation/outputs --save visualization/va_time_all.png
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot temporal polarization Va(t) for many runs in one graph."
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=Path("simulation") / "outputs",
        help="Directory containing run_* folders.",
    )
    parser.add_argument(
        "--latest-count",
        type=int,
        default=0,
        help="If > 0, include only the N most recent runs.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="If > 0, cap number of plotted runs after selection.",
    )
    parser.add_argument(
        "--vline-t",
        type=int,
        default=300,
        help="Timestep where the vertical reference line is drawn.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Optional output image path (png/pdf/svg). If omitted, opens interactive window.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=140,
        help="DPI used when saving figure.",
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


def as_float(props: Dict[str, str], key: str, default: float) -> float:
    value = props.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def as_int(props: Dict[str, str], key: str, default: int) -> int:
    value = props.get(key)
    if value is None:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def parse_trajectory(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Missing trajectory file: {path}")

    data = np.loadtxt(path, skiprows=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] != 7:
        raise ValueError(f"Expected 7 columns in trajectory, got {data.shape[1]} at {path}")
    return data


def compute_va_t(data: np.ndarray, props: Dict[str, str]) -> Tuple[np.ndarray, np.ndarray]:
    t = data[:, 0].astype(np.int64)
    vx = data[:, 4]
    vy = data[:, 5]

    n_steps = int(t.max()) + 1
    n_by_t = np.bincount(t, minlength=n_steps)

    sum_vx = np.bincount(t, weights=vx, minlength=n_steps)
    sum_vy = np.bincount(t, weights=vy, minlength=n_steps)

    n_from_props = as_int(props, "N", 0)
    n_particles = n_from_props if n_from_props > 0 else int(np.max(n_by_t))

    v0_from_props = as_float(props, "v0", -1.0)
    if v0_from_props > 0:
        denom = n_particles * v0_from_props
        va = np.sqrt(sum_vx * sum_vx + sum_vy * sum_vy) / denom
    else:
        speed = np.sqrt(vx * vx + vy * vy)
        sum_speed = np.bincount(t, weights=speed, minlength=n_steps)
        denom = np.where(sum_speed > 0.0, sum_speed, 1.0)
        va = np.sqrt(sum_vx * sum_vx + sum_vy * sum_vy) / denom

    t_axis = np.arange(n_steps, dtype=np.int64)
    return t_axis, va


def discover_runs(outputs_dir: Path) -> List[Path]:
    if not outputs_dir.exists() or not outputs_dir.is_dir():
        raise FileNotFoundError(f"outputs directory does not exist: {outputs_dir}")

    run_dirs = []
    for trajectory in outputs_dir.rglob("trajectory.txt"):
        run_dir = trajectory.parent
        if (run_dir / "properties.txt").exists():
            run_dirs.append(run_dir)

    run_dirs.sort(key=lambda p: p.stat().st_mtime)
    return run_dirs


def select_runs(run_dirs: List[Path], latest_count: int, max_runs: int) -> List[Path]:
    selected = run_dirs

    if latest_count > 0:
        selected = selected[-latest_count:]

    if max_runs > 0:
        selected = selected[:max_runs]

    return selected


def run_label(run_dir: Path, props: Dict[str, str]) -> str:
    eta = props.get("eta", "?")
    return rf"$\eta$={eta}"


def main() -> None:
    args = parse_args()

    if args.latest_count < 0:
        raise ValueError("--latest-count must be >= 0")
    if args.max_runs < 0:
        raise ValueError("--max-runs must be >= 0")
    if args.vline_t < 0:
        raise ValueError("--vline-t must be >= 0")

    run_dirs = discover_runs(args.outputs_dir.resolve())
    run_dirs = select_runs(run_dirs, args.latest_count, args.max_runs)

    if not run_dirs:
        raise ValueError("No run directories found to plot.")

    fig, ax = plt.subplots(figsize=(11.5, 6.5))

    for run_dir in run_dirs:
        props = parse_properties(run_dir / "properties.txt")
        data = parse_trajectory(run_dir / "trajectory.txt")
        t_axis, va = compute_va_t(data, props)

        ax.plot(t_axis, va, linewidth=1.4, alpha=0.9, label=run_label(run_dir, props))

    ax.set_xlabel(r"Tiempo de simulación ($t$)", fontsize=20)
    ax.set_ylabel(r"Polarización ($V_a$)", fontsize=20)
    ax.set_ylim(0.0, 1.02)
    ax.axvline(args.vline_t, color="#d62728", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.tick_params(axis="both", which="major", labelsize=20)
    ax.grid(alpha=0.25)

    # Put legend above the axes in horizontal layout to avoid covering curves.
    ncol = min(max(len(run_dirs), 1), 8)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=ncol,
        fontsize=20,
        frameon=False,
        handlelength=1.8,
        columnspacing=1.0,
    )

    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.9])

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=args.dpi)
        print(f"Saved figure: {args.save.resolve()}")
    else:
        plt.show()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Plot Va(t) with mean and standard deviation bands for each eta.

Groups runs by eta, aggregates up to 5 runs per eta, computes mean and std Va(t),
and displays them on a single figure with shaded uncertainty bands.

Examples:
- python visualization/plot_va_time_stats.py --outputs-dir simulation/outputs
- python visualization/plot_va_time_stats.py --outputs-dir simulation/outputs --runs-per-eta 3
- python visualization/plot_va_time_stats.py --outputs-dir simulation/outputs --save visualization/va_time_stats.png
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot Va(t) mean and std bands aggregated by eta."
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=Path("simulation") / "outputs",
        help="Directory containing run_* folders.",
    )
    parser.add_argument(
        "--runs-per-eta",
        type=int,
        default=5,
        help="Maximum number of runs to use per eta value.",
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


def group_runs_by_eta(
    run_dirs: List[Path], runs_per_eta: int
) -> Dict[float, List[Path]]:
    grouped: Dict[float, List[Path]] = defaultdict(list)

    for run_dir in run_dirs:
        props = parse_properties(run_dir / "properties.txt")
        eta = as_float(props, "eta", -1.0)
        if eta < 0:
            continue
        if len(grouped[eta]) < runs_per_eta:
            grouped[eta].append(run_dir)

    return grouped


def compute_stats_for_eta(run_dirs: List[Path]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute mean and std of Va(t) across multiple runs.
    Returns (t_axis, va_mean, va_std) with aligned time axis.
    """
    va_list: List[np.ndarray] = []
    common_t_max = 0

    for run_dir in run_dirs:
        props = parse_properties(run_dir / "properties.txt")
        data = parse_trajectory(run_dir / "trajectory.txt")
        t_axis, va = compute_va_t(data, props)
        va_list.append(va)
        common_t_max = max(common_t_max, len(va))

    if not va_list:
        return np.array([]), np.array([]), np.array([])

    # Pad all va arrays to common length with NaN
    va_padded = []
    for va in va_list:
        padded = np.full(common_t_max, np.nan)
        padded[: len(va)] = va
        va_padded.append(padded)

    va_array = np.array(va_padded)
    va_mean = np.nanmean(va_array, axis=0)
    va_std = np.nanstd(va_array, axis=0)

    t_axis = np.arange(common_t_max, dtype=np.int64)
    return t_axis, va_mean, va_std


def get_color_for_eta(eta: float, eta_values: List[float]) -> str:
    """Assign a color to each eta based on its position in the sorted list."""
    colors = [
        "#1f77b4",  # blue
        "#ff7f0e",  # orange
        "#2ca02c",  # green
        "#d62728",  # red
        "#9467bd",  # purple
        "#8c564b",  # brown
        "#e377c2",  # pink
        "#7f7f7f",  # gray
        "#bcbd22",  # olive
        "#17becf",  # cyan
    ]
    idx = eta_values.index(eta) % len(colors)
    return colors[idx]


def main() -> None:
    args = parse_args()

    if args.runs_per_eta <= 0:
        raise ValueError("--runs-per-eta must be > 0")

    run_dirs = discover_runs(args.outputs_dir.resolve())
    grouped = group_runs_by_eta(run_dirs, args.runs_per_eta)

    if not grouped:
        raise ValueError("No run directories found to plot.")

    eta_values = sorted(grouped.keys())

    fig, ax = plt.subplots(figsize=(11.5, 6.5))

    for eta in eta_values:
        run_list = grouped[eta]
        t_axis, va_mean, va_std = compute_stats_for_eta(run_list)

        if len(t_axis) == 0:
            continue

        color = get_color_for_eta(eta, eta_values)

        # Plot mean line
        ax.plot(t_axis, va_mean, color=color, linewidth=2.0, label=rf"$\eta$={eta:.2g}")

        # Plot std band
        va_lower = va_mean - va_std
        va_upper = va_mean + va_std
        ax.fill_between(t_axis, va_lower, va_upper, color=color, alpha=0.15)

    ax.set_xlabel(r"Tiempo de simulación ($t$)")
    ax.set_ylabel(r"Polarización ($V_a$)")
    ax.set_ylim(0.0, 1.02)
    ax.axvline(300, color="#d62728", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.grid(alpha=0.25)

    # Legend above in horizontal layout
    ncol = min(max(len(eta_values), 1), 8)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=ncol,
        fontsize=9,
        frameon=False,
        handlelength=2.0,
        columnspacing=1.2,
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

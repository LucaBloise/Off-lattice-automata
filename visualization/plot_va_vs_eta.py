#!/usr/bin/env python3
"""
Build Input vs Observable curve: Va as a function of eta, with error bars.

It reads simulation run folders, computes for each run:
- Va(t) from trajectory.txt
- scalar Va_run = mean_t>=t0 Va(t), where t0 is transient cutoff

Then groups runs by eta and computes:
- mean Va across runs
- std Va across runs (error bars)

Expected files per run directory:
- trajectory.txt   columns: t id x y vx vy theta
- properties.txt   key=value, must include eta, and ideally N, v0

Examples:
- python visualization/plot_va_vs_eta.py --outputs-dir outputs
- python visualization/plot_va_vs_eta.py --outputs-dir outputs --transient-step 200 --save visualization/va_vs_eta.png
- python visualization/plot_va_vs_eta.py --run-dir outputs/run_20260324_120000_001 --run-dir outputs/run_20260324_120500_010
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot Va vs eta with error bars from multiple runs.")
    parser.add_argument(
        "--run-dir",
        type=Path,
        action="append",
        default=[],
        help="Path to one run directory. Repeat to include many runs.",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=None,
        help="Directory containing run_* subfolders. If omitted, auto-detects outputs/.",
    )
    parser.add_argument(
        "--transient-step",
        type=int,
        default=200,
        help="Discard all timesteps t < transient-step when averaging Va(t).",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="standard",
        help="Scenario filter: standard, fixed_leader, circular_leader.",
    )
    parser.add_argument(
        "--min-runs-per-eta",
        type=int,
        default=1,
        help="Require at least this many runs per eta to include the eta in the final curve.",
    )
    parser.add_argument(
        "--eta-list",
        type=float,
        nargs="*",
        default=None,
        help="Optional eta filter. If provided, include only these eta values.",
    )
    parser.add_argument(
        "--eta-tol",
        type=float,
        default=1e-9,
        help="Tolerance used when filtering by --eta-list.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Optional path to save figure (png/pdf/svg). If omitted, opens interactive window.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional path to save aggregated table as CSV.",
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


def normalize_scenario(raw: str) -> str:
    value = raw.strip().lower()
    aliases = {
        "standard": "standard",
        "normal": "standard",
        "no_leader": "standard",
        "none": "standard",
        "fixed": "fixed_leader",
        "fixed_leader": "fixed_leader",
        "leader_fixed": "fixed_leader",
        "circular": "circular_leader",
        "circular_leader": "circular_leader",
        "leader_circular": "circular_leader",
    }
    if value in aliases:
        return aliases[value]
    raise ValueError(f"Unknown scenario value: {raw}")


def scenario_from_properties(props: Dict[str, str]) -> str:
    if "scenario" in props:
        return normalize_scenario(props["scenario"])

    model = props.get("model", "").strip().lower()
    if "fixed" in model:
        return "fixed_leader"
    if "circular" in model:
        return "circular_leader"
    return "standard"


def parse_trajectory(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Missing trajectory file: {path}")

    data = np.loadtxt(path, skiprows=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] != 7:
        raise ValueError(f"Expected 7 columns in trajectory, got {data.shape[1]} in {path}")
    return data


def compute_va_t(data: np.ndarray, props: Dict[str, str]) -> np.ndarray:
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

    return va


def default_outputs_dir() -> Path:
    candidates = [Path("outputs"), Path("simulation") / "outputs"]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return candidates[0]


def list_runs(outputs_dir: Path) -> List[Path]:
    if not outputs_dir.exists() or not outputs_dir.is_dir():
        raise FileNotFoundError(f"outputs directory does not exist: {outputs_dir}")

    run_dirs = set()
    for trajectory in outputs_dir.rglob("trajectory.txt"):
        run_dir = trajectory.parent
        if (run_dir / "properties.txt").exists():
            run_dirs.add(run_dir.resolve())

    return sorted(run_dirs)


def resolve_runs(args: argparse.Namespace) -> List[Path]:
    runs: List[Path] = []

    if args.outputs_dir is not None:
        runs.extend(list_runs(args.outputs_dir))
    elif not args.run_dir:
        runs.extend(list_runs(default_outputs_dir()))

    runs.extend(args.run_dir)

    unique: List[Path] = []
    seen = set()
    for run in runs:
        rr = run.resolve()
        if rr not in seen:
            seen.add(rr)
            unique.append(rr)

    if not unique:
        raise ValueError("No run directories found.")

    return unique


def eta_allowed(eta: float, eta_list: List[float] | None, tol: float) -> bool:
    if eta_list is None:
        return True
    return any(abs(eta - target) <= tol for target in eta_list)


def run_scalar_va(run_dir: Path, transient_step: int) -> Tuple[float, float, int, str]:
    properties = parse_properties(run_dir / "properties.txt")
    eta = as_float(properties, "eta", math.nan)
    if math.isnan(eta):
        raise ValueError(f"Missing numeric eta in properties.txt for run: {run_dir}")
    scenario = scenario_from_properties(properties)

    data = parse_trajectory(run_dir / "trajectory.txt")
    va_t = compute_va_t(data, properties)

    t0 = max(int(transient_step), 0)
    if t0 >= len(va_t):
        raise ValueError(
            f"transient-step={t0} is >= number of timesteps={len(va_t)} for run: {run_dir.name}"
        )

    va_scalar = float(np.mean(va_t[t0:]))
    return eta, va_scalar, len(va_t), scenario


def aggregate_by_eta(
    runs: List[Path],
    transient_step: int,
    eta_list: List[float] | None,
    eta_tol: float,
    min_runs_per_eta: int,
    scenario_filter: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Dict[float, List[Tuple[str, float]]]]:
    grouped: Dict[float, List[Tuple[str, float]]] = defaultdict(list)

    for run in runs:
        try:
            eta, va_scalar, _, run_scenario = run_scalar_va(run, transient_step)
        except Exception as exc:
            print(f"[warn] Skipping {run.name}: {exc}")
            continue

        if run_scenario != scenario_filter:
            continue

        if not eta_allowed(eta, eta_list, eta_tol):
            continue

        grouped[eta].append((run.name, va_scalar))

    etas_sorted = sorted(grouped.keys())

    eta_out: List[float] = []
    mean_out: List[float] = []
    std_out: List[float] = []
    n_out: List[int] = []

    for eta in etas_sorted:
        values = np.array([v for _, v in grouped[eta]], dtype=np.float64)
        if len(values) < min_runs_per_eta:
            print(
                f"[warn] eta={eta:g} has {len(values)} runs (< min-runs-per-eta={min_runs_per_eta}), excluded"
            )
            continue

        eta_out.append(eta)
        mean_out.append(float(np.mean(values)))
        std_out.append(float(np.std(values, ddof=1)) if len(values) > 1 else 0.0)
        n_out.append(int(len(values)))

    return (
        np.array(eta_out, dtype=np.float64),
        np.array(mean_out, dtype=np.float64),
        np.array(std_out, dtype=np.float64),
        np.array(n_out, dtype=np.int64),
        grouped,
    )


def write_csv(path: Path, eta: np.ndarray, mean: np.ndarray, std: np.ndarray, n: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["eta", "va_mean", "va_std", "n_runs", "va_sem"])
        for i in range(len(eta)):
            sem = std[i] / math.sqrt(n[i]) if n[i] > 0 else float("nan")
            writer.writerow([f"{eta[i]:.12g}", f"{mean[i]:.12g}", f"{std[i]:.12g}", int(n[i]), f"{sem:.12g}"])


def main() -> None:
    args = parse_args()

    if args.transient_step < 0:
        raise ValueError("--transient-step must be >= 0")
    if args.min_runs_per_eta <= 0:
        raise ValueError("--min-runs-per-eta must be >= 1")
    if args.eta_tol < 0:
        raise ValueError("--eta-tol must be >= 0")

    scenario_filter = normalize_scenario(args.scenario)

    runs = resolve_runs(args)
    eta, va_mean, va_std, n_runs, grouped = aggregate_by_eta(
        runs=runs,
        transient_step=args.transient_step,
        eta_list=args.eta_list,
        eta_tol=args.eta_tol,
        min_runs_per_eta=args.min_runs_per_eta,
        scenario_filter=scenario_filter,
    )

    if len(eta) == 0:
        raise ValueError("No eta groups available after filtering/validation.")

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.errorbar(
        eta,
        va_mean,
        yerr=va_std,
        fmt="o-",
        color="#1f77b4",
        ecolor="#1f77b4",
        elinewidth=1.2,
        capsize=3,
        markersize=5,
        linewidth=1.6,
    )

    ax.set_xlabel(r"amplitud de ruido ($\eta$)", fontsize=20)
    ax.set_ylabel(r"polarizacion ($v_{a}$)", fontsize=20)
    ax.set_title(
        f"Input vs Observable: Va(eta), scenario={scenario_filter}, transient cutoff t >= {args.transient_step}"
    )
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    if args.csv is not None:
        write_csv(args.csv, eta, va_mean, va_std, n_runs)
        print(f"Saved CSV: {args.csv.resolve()}")

    print("Included runs by eta:")
    for eta_value in sorted(grouped.keys()):
        count = len(grouped[eta_value])
        print(f"  eta={eta_value:g}: {count} runs")

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=args.dpi)
        print(f"Saved figure: {args.save.resolve()}")
    else:
        plt.show()


if __name__ == "__main__":
    main()

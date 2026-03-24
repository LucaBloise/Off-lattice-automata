#!/usr/bin/env python3
"""
Compare Va(eta) curves for the three scenarios in one figure:
- standard
- fixed_leader
- circular_leader

Uses the same aggregation criterion as plot_va_vs_eta.py:
1) per run: Va_run = mean_t>=transient_step Va(t)
2) per eta and scenario: mean/std across runs
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from plot_va_vs_eta import aggregate_by_eta, resolve_runs


SCENARIOS = ["standard", "fixed_leader", "circular_leader"]
COLORS = {
    "standard": "#1f77b4",
    "fixed_leader": "#d62728",
    "circular_leader": "#2ca02c",
}
LABELS = {
    "standard": "Standard (no leader)",
    "fixed_leader": "Fixed-direction leader",
    "circular_leader": "Circular leader",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Va vs eta across scenarios.")
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
        help="Directory containing run folders. If omitted, auto-detects outputs.",
    )
    parser.add_argument(
        "--transient-step",
        type=int,
        default=200,
        help="Discard all timesteps t < transient-step when averaging Va(t).",
    )
    parser.add_argument(
        "--min-runs-per-eta",
        type=int,
        default=1,
        help="Require at least this many runs for each eta/scenario point.",
    )
    parser.add_argument(
        "--eta-list",
        type=float,
        nargs="*",
        default=None,
        help="Optional eta filter.",
    )
    parser.add_argument(
        "--eta-tol",
        type=float,
        default=1e-9,
        help="Tolerance for eta filtering.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Optional output image path. If omitted, opens interactive window.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=140,
        help="DPI used when saving figure.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.transient_step < 0:
        raise ValueError("--transient-step must be >= 0")
    if args.min_runs_per_eta <= 0:
        raise ValueError("--min-runs-per-eta must be >= 1")

    runs = resolve_runs(args)

    fig, ax = plt.subplots(figsize=(8.8, 5.2))

    plotted_any = False
    for scenario in SCENARIOS:
        eta, va_mean, va_std, n_runs, grouped = aggregate_by_eta(
            runs=runs,
            transient_step=args.transient_step,
            eta_list=args.eta_list,
            eta_tol=args.eta_tol,
            min_runs_per_eta=args.min_runs_per_eta,
            scenario_filter=scenario,
        )

        if len(eta) == 0:
            print(f"[warn] No points available for scenario={scenario}")
            continue

        plotted_any = True
        ax.errorbar(
            eta,
            va_mean,
            yerr=va_std,
            fmt="o-",
            color=COLORS[scenario],
            ecolor=COLORS[scenario],
            capsize=3,
            markersize=5,
            linewidth=1.6,
            label=LABELS[scenario],
        )

        for x, y, n in zip(eta, va_mean, n_runs):
            ax.annotate(f"n={n}", (x, y), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7)

        print(f"Included points for scenario={scenario}:")
        for eta_value in sorted(grouped.keys()):
            print(f"  eta={eta_value:g}: {len(grouped[eta_value])} runs")

    if not plotted_any:
        raise ValueError("No points to plot. Check runs/scenario coverage and filters.")

    ax.set_xlabel("eta")
    ax.set_ylabel("Va (stationary mean)")
    ax.set_title(f"Va vs eta comparison across scenarios (t >= {args.transient_step})")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=args.dpi)
        print(f"Saved figure: {args.save.resolve()}")
    else:
        plt.show()


if __name__ == "__main__":
    main()

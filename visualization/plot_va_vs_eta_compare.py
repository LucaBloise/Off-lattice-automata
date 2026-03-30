#!/usr/bin/env python3
"""
Compare Va(eta) and its error for the three scenarios in separated plots:
- standard
- fixed_leader
- circular_leader

Uses the same aggregation criterion as plot_va_vs_eta.py.
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
    "standard": "Estándar (sin líder)",
    "fixed_leader": "Líder con dirección fija",
    "circular_leader": "Líder circular",
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
        "--stationary-end",
        type=int,
        default=1000,
        help="Last timestep (inclusive) to include in the stationary average. Default: 1000.",
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
    if args.stationary_end <= args.transient_step:
        raise ValueError("--stationary-end must be > --transient-step")
    if args.min_runs_per_eta <= 0:
        raise ValueError("--min-runs-per-eta must be >= 1")

    runs = resolve_runs(args)

    fig_va, ax_va = plt.subplots(figsize=(8.8, 5.2))
    fig_err, ax_err = plt.subplots(figsize=(8.8, 5.2))

    plotted_any = False
    for scenario in SCENARIOS:
        eta, va_mean, va_std, _n_runs, grouped = aggregate_by_eta(
            runs=runs,
            transient_step=args.transient_step,
            stationary_end=args.stationary_end,
            eta_list=args.eta_list,
            eta_tol=args.eta_tol,
            min_runs_per_eta=args.min_runs_per_eta,
            scenario_filter=scenario,
        )

        if len(eta) == 0:
            print(f"[warn] No points available for scenario={scenario}")
            continue

        plotted_any = True
        ax_va.plot(
            eta,
            va_mean,
            "o-",
            color=COLORS[scenario],
            markersize=5,
            linewidth=1.6,
            label=LABELS[scenario],
        )

        ax_err.plot(
            eta,
            va_std,
            "o-",
            color=COLORS[scenario],
            markersize=5,
            linewidth=1.6,
            label=LABELS[scenario],
        )

        print(f"Included points for scenario={scenario}:")
        for eta_value in sorted(grouped.keys()):
            print(f"  eta={eta_value:g}: {len(grouped[eta_value])} runs")

    if not plotted_any:
        raise ValueError("No points to plot. Check runs/scenario coverage and filters.")

    ax_va.set_xlabel(r"Amplitud de ruido ($\eta$)", fontsize=20)
    ax_va.set_ylabel(r"Polarización ($V_a$)", fontsize=20)
    ax_va.set_ylim(0.0, 1.02)
    ax_va.grid(alpha=0.25)
    ax_va.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=3,
        fontsize=16,
        frameon=False,
    )
    ax_va.tick_params(axis="both", which="major", labelsize=16)
    fig_va.tight_layout(rect=[0.0, 0.0, 1.0, 0.9])

    ax_err.set_xlabel(r"Amplitud de ruido ($\eta$)", fontsize=20)
    ax_err.set_ylabel(r"Desvío estándar ($\sigma_{V_a}$)", fontsize=20)
    ax_err.grid(alpha=0.25)
    ax_err.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=3,
        fontsize=16,
        frameon=False,
    )
    ax_err.tick_params(axis="both", which="major", labelsize=16)
    fig_err.tight_layout(rect=[0.0, 0.0, 1.0, 0.9])

    if args.save is not None:
        save_va = args.save.parent / f"{args.save.stem}_va{args.save.suffix}"
        save_err = args.save.parent / f"{args.save.stem}_err{args.save.suffix}"
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig_va.savefig(save_va, dpi=args.dpi)
        fig_err.savefig(save_err, dpi=args.dpi)
        print(f"Saved figures:")
        print(f"  Va:    {save_va.resolve()}")
        print(f"  Error: {save_err.resolve()}")
    else:
        plt.show()


if __name__ == "__main__":
    main()

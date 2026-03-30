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
import importlib
import math
from pathlib import Path
import tempfile
from typing import Dict, Tuple

import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation
from matplotlib.widgets import Button, Slider
import numpy as np


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters in text for mathtext."""
    replacements = {'\\': r'\textbackslash ', '$': r'\$', '%': r'\%', '#': r'\#',
                    '&': r'\&', '_': r'\_', '{': r'\{', '}': r'\}'}
    result = text
    for char, escaped in replacements.items():
        result = result.replace(char, escaped)
    return result


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


def compute_va_per_step(data: np.ndarray, props: Dict[str, str], n_steps: int) -> np.ndarray:
    t = data[:, 0].astype(np.int64)
    vx = data[:, 4]
    vy = data[:, 5]

    n_by_t = np.bincount(t, minlength=n_steps)
    sum_vx = np.bincount(t, weights=vx, minlength=n_steps)
    sum_vy = np.bincount(t, weights=vy, minlength=n_steps)

    n_from_props = as_int(props, "N", 0)
    n_particles = n_from_props if n_from_props > 0 else int(np.max(n_by_t))

    v0_from_props = as_float(props, "v0", -1.0)
    if v0_from_props > 0:
        denom = n_particles * v0_from_props
        return np.sqrt(sum_vx * sum_vx + sum_vy * sum_vy) / denom

    speed = np.sqrt(vx * vx + vy * vy)
    sum_speed = np.bincount(t, weights=speed, minlength=n_steps)
    denom = np.where(sum_speed > 0.0, sum_speed, 1.0)
    return np.sqrt(sum_vx * sum_vx + sum_vy * sum_vy) / denom


def convert_gif_to_mp4(gif_path: Path, mp4_path: Path, fps: int) -> bool:
    try:
        imageio = importlib.import_module("imageio.v2")
    except Exception:
        return False


def save_mp4_with_opencv(fig, update_fn, n_frames: int, output_path: Path, fps: int) -> bool:
    try:
        cv2 = importlib.import_module("cv2")
    except Exception:
        return False

    writer = None
    try:
        update_fn(0)
        fig.canvas.draw()
        first = np.asarray(fig.canvas.buffer_rgba())
        height, width = first.shape[0], first.shape[1]

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, float(fps), (width, height))
        if not writer.isOpened():
            return False

        for frame_idx in range(n_frames):
            update_fn(frame_idx)
            fig.canvas.draw()
            rgba = np.asarray(fig.canvas.buffer_rgba())
            bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
            writer.write(bgr)

        writer.release()
        return True
    except Exception:
        if writer is not None:
            writer.release()
        return False

    try:
        reader = imageio.get_reader(str(gif_path))
        writer = imageio.get_writer(
            str(mp4_path),
            format="FFMPEG",
            fps=fps,
            codec="libx264",
            pixelformat="yuv420p",
        )
        for frame in reader:
            writer.append_data(frame)
        writer.close()
        reader.close()
        return True
    except Exception:
        return False


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

    va_per_step = compute_va_per_step(trajectory_data, properties, n_steps)

    follower_indices = np.arange(n_particles)
    if valid_leader:
        follower_indices = np.array([idx for idx in range(n_particles) if idx != leader_id], dtype=np.int64)

    fig, ax = plt.subplots(figsize=tuple(args.figsize))
    ax.set_xlim(0.0, L)
    ax.set_ylim(0.0, L)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x", fontsize=20)
    ax.set_ylabel("y", fontsize=20)
    ax.tick_params(axis="both", which="major", labelsize=16)
    
    # Build title with escaped parameters
    scenario_safe = _escape_latex(scenario)
    density_safe = _escape_latex(density)
    eta_safe = _escape_latex(eta)
    title_text = (
        f"$\\mathrm{{Condiciones}}={scenario_safe}$\n"
        f"$\\rho={density_safe}$, $\\eta={eta_safe}$"
    )
    ax.set_title(title_text, pad=18, fontsize=18)

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
            label="Líder",
        )
        ax.legend(
            loc="upper left",
            bbox_to_anchor=(1.12, 1.0),
            ncol=1,
            fontsize=14,
            frameon=True,
        )

    colorbar = fig.colorbar(quiver, ax=ax, pad=0.02)
    colorbar.set_label("ángulo de velocidad (rad)", fontsize=16)
    colorbar.ax.tick_params(labelsize=14)

    step_text = ax.text(
        0.98,
        0.98,
        "",
        transform=ax.transAxes,
        va="top",
        ha="right",
        fontsize=16,
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
        artists = [quiver, step_text]

        if valid_leader and leader_quiver is not None and leader_marker is not None:
            leader_offsets = np.array([[x[step, leader_id], y[step, leader_id]]])
            leader_quiver.set_offsets(leader_offsets)
            leader_quiver.set_UVC(
                np.array([vx[step, leader_id] * args.vector_length_scale]),
                np.array([vy[step, leader_id] * args.vector_length_scale]),
            )
            leader_marker.set_offsets(leader_offsets)
            artists.extend([leader_quiver, leader_marker])

        step_text.set_text(f"$t={step}$ / {n_steps - 1}\n$va={va_per_step[step]:.4f}$")
        return tuple(artists)

    n_frames = len(frame_indices)

    # Save mode: plain FuncAnimation, no interactive widgets.
    if args.save is not None:
        animation = FuncAnimation(
            fig,
            update,
            frames=n_frames,
            interval=args.interval,
            blit=False,
            repeat=False,
        )
        args.save.parent.mkdir(parents=True, exist_ok=True)
        suffix = args.save.suffix.lower()
        print(f"Guardando animación a {args.save.resolve()}...")
        if suffix == ".gif":
            animation.save(args.save, writer="pillow", fps=args.fps, dpi=args.dpi)
        elif suffix in {".mp4", ".mkv", ".avi", ".mov"}:
            saved_video = False
            if FFMpegWriter.isAvailable():
                try:
                    animation.save(args.save, writer="ffmpeg", fps=args.fps, dpi=args.dpi)
                    saved_video = True
                except Exception:
                    print("ffmpeg falló al codificar, probando alternativa OpenCV...")
            if not saved_video and suffix == ".mp4":
                if save_mp4_with_opencv(fig, update, n_frames, args.save, args.fps):
                    print("MP4 guardado usando alternativa OpenCV")
                    saved_video = True
                else:
                    print("OpenCV fallback unavailable, trying imageio-ffmpeg fallback for MP4...")

            if not saved_video and suffix == ".mp4":
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_gif = Path(tmp_dir) / "tmp_animation.gif"
                    animation.save(tmp_gif, writer="pillow", fps=args.fps, dpi=args.dpi)
                    if convert_gif_to_mp4(tmp_gif, args.save, args.fps):
                        print("Saved MP4 using imageio-ffmpeg fallback")
                        saved_video = True
                    else:
                        print("imageio-ffmpeg fallback unavailable, falling back to GIF")
                        gif_path = args.save.with_suffix(".gif")
                        animation.save(gif_path, writer="pillow", fps=args.fps, dpi=args.dpi)
                        print(f"Saved as GIF instead: {gif_path.resolve()}")
                        return
            if not saved_video:
                animation.save(args.save, fps=args.fps, dpi=args.dpi)
        else:
            animation.save(args.save, fps=args.fps, dpi=args.dpi)
        print(f"Guardado: {args.save.resolve()}")
        return

    # Interactive mode: slider + play/pause button + keyboard controls.
    fig.subplots_adjust(bottom=0.18)

    state = {"frame": 0, "paused": False}

    # Create controls before first render so callbacks can safely reference widgets.
    ax_slider = fig.add_axes([0.12, 0.07, 0.68, 0.03])
    frame_slider = Slider(ax_slider, "Frame", 0, n_frames - 1, valinit=0, valstep=1)
    ax_btn = fig.add_axes([0.83, 0.055, 0.10, 0.055])
    btn_playpause = Button(ax_btn, "Pause")

    def render_frame(frame_number: int) -> None:
        frame_number = max(0, min(int(frame_number), n_frames - 1))
        state["frame"] = frame_number
        update(frame_number)
        frame_slider.eventson = False
        frame_slider.set_val(frame_number)
        frame_slider.eventson = True
        fig.canvas.draw_idle()

    def frame_gen():
        while True:
            yield state["frame"]
            if not state["paused"]:
                state["frame"] = (state["frame"] + 1) % n_frames

    def anim_update(frame_number: int):
        render_frame(frame_number)
        return []

    animation = FuncAnimation(
        fig,
        anim_update,
        frames=frame_gen(),
        interval=args.interval,
        blit=False,
        cache_frame_data=False,
    )

    def toggle_pause() -> None:
        state["paused"] = not state["paused"]
        btn_playpause.label.set_text("Play" if state["paused"] else "Pause")
        fig.canvas.draw_idle()

    def on_slider_change(val: float) -> None:
        render_frame(int(val))

    frame_slider.on_changed(on_slider_change)
    btn_playpause.on_clicked(lambda _event: toggle_pause())

    def on_key(event) -> None:
        if event.key == " ":
            toggle_pause()
        elif event.key == "left":
            state["paused"] = True
            btn_playpause.label.set_text("Play")
            render_frame(state["frame"] - 1)
        elif event.key == "right":
            state["paused"] = True
            btn_playpause.label.set_text("Play")
            render_frame(state["frame"] + 1)

    fig.canvas.mpl_connect("key_press_event", on_key)

    print("Controles: ESPACIO/botón pausa-reproducción | IZQUIERDA/DERECHA paso | barra desplazamiento")
    plt.show()


if __name__ == "__main__":
    main()

# 게임에서 지형을 만들 때 쓰는 특수한 수학 기법 #프로그래밍 #펄린노이즈 #수학 #절차적생성
# https://www.youtube.com/shorts/kY9TYQYxCZM

import time
from pathlib import Path

import perlin
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.axes3d import Axes3D
from tqdm import tqdm

DOMAIN_MAX = 1
CELL_DIVISION = 100
FREQUENCY = 10
Z_MIN, Z_MAX = -0.1, 0.1
TARGET_FPS = 60
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "heightfield_cpu"


def compute_z(
    generator: perlin.Perlin,
    X_fine: np.ndarray,
    Y_fine: np.ndarray,
    t_noise: float,
) -> np.ndarray:
    Z = np.zeros_like(X_fine)
    for row in range(Z.shape[0]):
        for col in range(Z.shape[1]):
            Z[row, col] = (
                generator.noise(
                    X_fine[row, col] * FREQUENCY,
                    Y_fine[row, col] * FREQUENCY,
                    t_noise,
                )
                / FREQUENCY
            )
    return Z


def benchmark_compute(
    generator: perlin.Perlin,
    X_fine: np.ndarray,
    Y_fine: np.ndarray,
    frame_count: int,
) -> None:
    sample_count = frame_count * X_fine.size
    frame_seconds: list[float] = []

    for tidx in tqdm(range(frame_count), desc="Computing noise", unit="frame"):
        t_phase = tidx / frame_count
        t_noise = t_phase * 0.5
        start: float = time.perf_counter()
        compute_z(generator, X_fine, Y_fine, t_noise)
        frame_seconds.append(time.perf_counter() - start)

    total = sum(frame_seconds)
    print(f"frames: {frame_count}")
    print(f"grid: {CELL_DIVISION} x {CELL_DIVISION}")
    print(f"samples: {sample_count:,}")
    print(f"total: {total:.3f} s")
    print(f"per frame: {total / frame_count * 1000:.2f} ms")
    print(f"per sample: {total / sample_count * 1e6:.2f} us")


def _draw_surface(
    ax: plt.Axes,
    X_fine: np.ndarray,
    Y_fine: np.ndarray,
    Z: np.ndarray,
    t_phase: float,
    t_noise: float,
) -> None:
    ax.clear()
    ax.plot_surface(
        X_fine,
        Y_fine,
        Z,
        cmap="viridis",
        rcount=CELL_DIVISION,
        ccount=CELL_DIVISION,
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("noise")
    ax.set_title(f"t={t_phase:.3f}, sin(2pi*t)={t_noise:.3f}")
    ax.set_zlim(Z_MIN, Z_MAX)
    ax.set_aspect("equal")


def main() -> None:
    frame_count = 60 * 5
    generator = perlin.Perlin(6789)

    x_fine: np.ndarray = np.linspace(0, DOMAIN_MAX, CELL_DIVISION)
    y_fine: np.ndarray = np.linspace(0, DOMAIN_MAX, CELL_DIVISION)
    X_fine, Y_fine = np.meshgrid(x_fine, y_fine)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "anim_perlin_2002.mp4"
    interval_ms: float = 1000 / TARGET_FPS

    fig: Figure = plt.figure(figsize=(10, 10))
    ax: Axes3D = fig.add_subplot(111, projection="3d")

    t_phase_0: float = 0.0
    t_noise_0 = np.sin(2 * np.pi * t_phase_0)
    Z_0: np.ndarray = compute_z(generator, X_fine, Y_fine, t_noise_0)
    _draw_surface(ax, X_fine, Y_fine, Z_0, t_phase_0, t_noise_0)

    def on_frame(tidx: int) -> None:
        t_phase: float = tidx / frame_count
        t_noise = np.sin(2 * np.pi * t_phase)
        Z: np.ndarray = compute_z(generator, X_fine, Y_fine, t_noise)
        _draw_surface(ax, X_fine, Y_fine, Z, t_phase, t_noise)

    animation: FuncAnimation = FuncAnimation(
        fig,
        on_frame,
        frames=frame_count,
        interval=interval_ms,
    )

    with tqdm(
        total=frame_count,
        desc=f"Saving {output_path}",
        unit="frame",
    ) as pbar:

        def progress_callback(i: int, n: int) -> None:
            pbar.total = n
            pbar.n = i + 1
            pbar.refresh()

        animation.save(
            filename=str(output_path),
            fps=TARGET_FPS,
            progress_callback=progress_callback,
        )


if __name__ == "__main__":
    main()

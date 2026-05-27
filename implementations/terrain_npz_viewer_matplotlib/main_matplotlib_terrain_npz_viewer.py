from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
COMMON_DIR = PROJECT_ROOT / "implementations" / "terrain_generation_common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from terrain_npz_loader import load_terrain, newest_export  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="View exported terrain_generation .npz files with Matplotlib.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to an exported terrain .npz file. Defaults to the newest export.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="Surface downsample stride. Defaults to full resolution.",
    )
    parser.add_argument(
        "--save",
        help="Optional path to save a PNG preview instead of only opening a window.",
    )
    parser.add_argument(
        "--surface-coords",
        choices=("world", "grid"),
        default="world",
        help="Coordinate system for the 3D surface axes.",
    )
    return parser.parse_args()


def draw_viewer(
    path: Path,
    positions: np.ndarray,
    heights: np.ndarray,
    metadata: dict[str, Any],
    stride: int,
    surface_coords: str,
) -> plt.Figure:
    stride = max(1, int(stride))
    world_x = positions[:, :, 0]
    world_z = positions[:, :, 2]
    height = heights
    rows, cols = height.shape
    grid_x, grid_z = np.meshgrid(
        np.arange(cols, dtype="f4"),
        np.arange(rows, dtype="f4"),
    )

    if surface_coords == "grid":
        surface_x = grid_x
        surface_z = grid_z
        surface_xlabel = "grid column"
        surface_ylabel = "grid row"
    else:
        surface_x = world_x
        surface_z = world_z
        surface_xlabel = "world x"
        surface_ylabel = "world z"

    surface_x_view = surface_x[::stride, ::stride]
    surface_z_view = surface_z[::stride, ::stride]
    height_view = height[::stride, ::stride]

    backend = metadata.get("backend", "unknown")
    resolution = metadata.get("resolution", f"{rows}x{cols}")
    layer_count = metadata.get("layer_count", "?")
    title = (
        f"{path.name} | backend={backend} | resolution={resolution} | "
        f"grid={rows}x{cols} | layers={layer_count}"
    )

    fig = plt.figure(figsize=(14, 7))
    fig.suptitle(title)

    ax_map = fig.add_subplot(1, 2, 1)
    image = ax_map.imshow(
        height,
        origin="lower",
        cmap="terrain",
        extent=(-0.5, cols - 0.5, -0.5, rows - 0.5),
        aspect="equal",
    )
    ax_map.set_title(f"Height Map ({rows}x{cols} samples)")
    ax_map.set_xlabel("grid column")
    ax_map.set_ylabel("grid row")
    fig.colorbar(image, ax=ax_map, shrink=0.78, label="height")

    ax_surface = fig.add_subplot(1, 2, 2, projection="3d")
    ax_surface.plot_surface(
        surface_x_view,
        surface_z_view,
        height_view,
        cmap="terrain",
        linewidth=0,
        antialiased=True,
        rstride=1,
        cstride=1,
    )
    ax_surface.set_title(
        f"3D Surface ({surface_coords} coords, {height_view.shape[0]}x{height_view.shape[1]} samples)"
    )
    ax_surface.set_xlabel(surface_xlabel)
    ax_surface.set_ylabel(surface_ylabel)
    ax_surface.set_zlabel("height")
    set_axes_equal(ax_surface)
    ax_surface.view_init(elev=35, azim=-135)

    fig.tight_layout()
    return fig


def set_axes_equal(ax: Any) -> None:
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    y_range = abs(y_limits[1] - y_limits[0])
    z_range = abs(z_limits[1] - z_limits[0])
    radius = max(x_range, y_range, z_range) * 0.5

    x_middle = sum(x_limits) * 0.5
    y_middle = sum(y_limits) * 0.5
    z_middle = sum(z_limits) * 0.5

    ax.set_xlim3d(x_middle - radius, x_middle + radius)
    ax.set_ylim3d(y_middle - radius, y_middle + radius)
    ax.set_zlim3d(z_middle - radius, z_middle + radius)


def main() -> None:
    args = parse_args()
    path = Path(args.path).resolve() if args.path else newest_export()
    if not path.exists():
        raise FileNotFoundError(path)

    positions, heights, metadata = load_terrain(path)
    print(f"Loaded: {path}")
    print(f"positions: {positions.shape}, heights: {heights.shape}")
    print(
        "world range: "
        f"x={positions[:, :, 0].min():.6g}..{positions[:, :, 0].max():.6g}, "
        f"z={positions[:, :, 2].min():.6g}..{positions[:, :, 2].max():.6g}, "
        f"height={heights.min():.6g}..{heights.max():.6g}"
    )
    if metadata:
        print(
            "metadata: "
            f"backend={metadata.get('backend')}, "
            f"resolution={metadata.get('resolution')}, "
            f"layers={metadata.get('layer_count')}"
        )

    fig = draw_viewer(
        path,
        positions,
        heights,
        metadata,
        args.stride,
        args.surface_coords,
    )
    if args.save:
        save_path = Path(args.save).resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=160)
        print(f"Saved preview: {save_path}")
    else:
        plt.show()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"terrain npz viewer error: {exc}", file=sys.stderr)
        raise

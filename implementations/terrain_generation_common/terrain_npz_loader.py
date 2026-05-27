from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "exports" / "terrain_generation"


def newest_export(export_dir: Path | str = DEFAULT_EXPORT_DIR) -> Path:
    directory = Path(export_dir)
    files = sorted(directory.glob("*.npz"), key=lambda path: path.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No exported terrain .npz files found in {directory}")

    app_exports = [
        path
        for path in files
        if path.name.startswith(("terrain_cpu_", "terrain_gpu_"))
    ]
    return (app_exports or files)[-1]


def load_metadata(data: np.lib.npyio.NpzFile) -> dict[str, Any]:
    if "metadata_json" not in data:
        return {}

    raw = data["metadata_json"]
    if raw.shape == ():
        raw_value = raw.item()
    else:
        raw_value = str(raw)
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8")
    return json.loads(str(raw_value))


def infer_grid_shape(
    data: np.lib.npyio.NpzFile,
    metadata: dict[str, Any],
) -> tuple[int, int]:
    grid_shape = metadata.get("grid_shape") or metadata.get("height_shape")
    if grid_shape and len(grid_shape) == 2:
        return int(grid_shape[0]), int(grid_shape[1])

    resolution = metadata.get("resolution")
    if resolution is not None:
        resolution = int(resolution)
        return resolution, resolution

    sample = data["heights"] if "heights" in data else data["vertices"]
    count = int(sample.shape[0])
    side = int(round(count**0.5))
    if side * side == count:
        return side, side

    raise ValueError(
        f"Cannot infer grid shape from arrays. Element count is {count}, not square."
    )


def load_terrain_npz(path: Path | str) -> dict[str, Any]:
    terrain_path = Path(path).resolve()
    with np.load(terrain_path) as data:
        metadata = load_metadata(data)
        rows, cols = infer_grid_shape(data, metadata)

        if "vertices" in data:
            vertices = data["vertices"].astype("f4")
            positions = vertices[:, 0:3]
            normals = vertices[:, 3:6]
            heights = vertices[:, 6]
        else:
            positions = data["positions"].astype("f4")
            if "normals" in data:
                normals = data["normals"].astype("f4")
            else:
                normals = np.zeros_like(positions, dtype="f4")
                normals[:, 1] = 1.0
            heights = data["heights"].astype("f4")
            vertices = np.concatenate(
                [positions, normals, heights.reshape((-1, 1))],
                axis=1,
            ).astype("f4")

        if "indices" not in data:
            raise ValueError(f"Terrain export has no indices array: {terrain_path}")
        indices = data["indices"].astype("u4")

    expected = rows * cols
    if vertices.shape != (expected, 7):
        raise ValueError(f"Expected vertices shape ({expected}, 7), got {vertices.shape}")
    if positions.shape != (expected, 3):
        raise ValueError(f"Expected positions shape ({expected}, 3), got {positions.shape}")
    if normals.shape != (expected, 3):
        raise ValueError(f"Expected normals shape ({expected}, 3), got {normals.shape}")
    if heights.shape != (expected,):
        raise ValueError(f"Expected heights shape ({expected},), got {heights.shape}")

    if indices.ndim == 1:
        if indices.size % 3 != 0:
            raise ValueError(f"Flat indices length is not divisible by 3: {indices.size}")
        indices_tri = indices.reshape((-1, 3))
    elif indices.ndim == 2 and indices.shape[1] == 3:
        indices_tri = indices
    else:
        raise ValueError(f"Expected triangle indices shape (n, 3), got {indices.shape}")

    height_min = float(np.min(heights))
    height_max = float(np.max(heights))
    height_scale = max(float(np.max(np.abs(heights))), 0.001)

    return {
        "path": terrain_path,
        "metadata": metadata,
        "rows": rows,
        "cols": cols,
        "vertices": vertices,
        "positions": positions,
        "normals": normals,
        "heights": heights,
        "positions_grid": positions.reshape(rows, cols, 3),
        "normals_grid": normals.reshape(rows, cols, 3),
        "heights_grid": heights.reshape(rows, cols),
        "indices": indices_tri.reshape(-1),
        "indices_tri": indices_tri,
        "height_min": height_min,
        "height_max": height_max,
        "height_scale": height_scale,
    }


def load_terrain(path: Path | str) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    terrain = load_terrain_npz(path)
    return terrain["positions_grid"], terrain["heights_grid"], terrain["metadata"]


def load_exported_mesh(path: Path | str) -> dict[str, Any]:
    return load_terrain_npz(path)

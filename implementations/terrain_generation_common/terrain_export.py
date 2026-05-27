from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any

import numpy as np

from terrain_layers import LAYER_KIND_NAMES, TerrainLayer, TerrainStack


def export_terrain_npz(
    output_dir: str,
    backend_label: str,
    resolution: int,
    palette_name: str,
    stack: TerrainStack,
    vertex_bytes: bytes,
    index_bytes: bytes,
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"terrain_{backend_label.lower()}_{resolution}_{timestamp}.npz"
    path = os.path.join(output_dir, filename)

    vertices = np.frombuffer(vertex_bytes, dtype="f4").reshape((-1, 7)).copy()
    indices = np.frombuffer(index_bytes, dtype="u4").reshape((-1, 3)).copy()
    metadata = {
        "format": "perlin-in-hand terrain npz",
        "version": 1,
        "backend": backend_label,
        "resolution": int(resolution),
        "palette": palette_name,
        "vertex_layout": ["pos_x", "pos_y", "pos_z", "normal_x", "normal_y", "normal_z", "height"],
        "vertex_shape": list(vertices.shape),
        "grid_shape": [int(resolution), int(resolution)],
        "height_shape": [int(resolution), int(resolution)],
        "index_shape": list(indices.shape),
        "index_layout": "triangles_u32",
        "layer_count": len(stack.layers),
        "layers": [_layer_to_dict(layer) for layer in stack.layers],
    }

    np.savez_compressed(
        path,
        vertices=vertices,
        positions=vertices[:, 0:3],
        normals=vertices[:, 3:6],
        heights=vertices[:, 6],
        indices=indices,
        metadata_json=np.array(json.dumps(metadata, ensure_ascii=False, indent=2)),
    )
    return path


def _layer_to_dict(layer: TerrainLayer) -> dict[str, Any]:
    return {
        "kind": LAYER_KIND_NAMES[layer.kind],
        "kind_id": int(layer.kind),
        "octaves": int(layer.octaves),
        "frequency": float(layer.frequency),
        "amplitude": float(layer.amplitude),
        "persistence": float(layer.persistence),
        "lacunarity": float(layer.lacunarity),
        "seed_x": float(layer.seed_x),
        "seed_y": float(layer.seed_y),
        "rotation": float(layer.rotation),
        "valley_power": float(layer.valley_power),
        "warp_strength": float(layer.warp_strength),
        "warp_frequency": float(layer.warp_frequency),
        "warp_seed_x": float(layer.warp_seed_x),
        "warp_seed_y": float(layer.warp_seed_y),
        "enabled": bool(layer.enabled),
    }

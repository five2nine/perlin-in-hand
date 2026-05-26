from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import math
import random

import numpy as np


MAX_LAYERS = 16
MAX_OCTAVES = 3


class LayerKind(IntEnum):
    SIMPLE = 0
    FBM = 1
    RIDGED = 2
    BILLOW = 3
    VALLEY = 4
    WARPED = 5


LAYER_KIND_NAMES = {
    LayerKind.SIMPLE: "Simple",
    LayerKind.FBM: "fBm",
    LayerKind.RIDGED: "Ridged",
    LayerKind.BILLOW: "Billow",
    LayerKind.VALLEY: "Valley",
    LayerKind.WARPED: "Warped",
}


@dataclass(slots=True)
class TerrainLayer:
    kind: LayerKind
    octaves: int = 1
    frequency: float = 6.0
    amplitude: float = 0.08
    persistence: float = 0.5
    lacunarity: float = 2.0
    seed_x: float = 0.0
    seed_y: float = 0.0
    rotation: float = 0.0
    valley_power: float = 2.5
    warp_strength: float = 0.0
    warp_frequency: float = 4.0
    warp_seed_x: float = 19.17
    warp_seed_y: float = -47.63
    enabled: bool = True

    def __post_init__(self) -> None:
        self.kind = LayerKind(self.kind)
        self.octaves = max(1, min(MAX_OCTAVES, int(self.octaves)))
        self.frequency = max(0.001, float(self.frequency))
        self.amplitude = float(self.amplitude)
        self.persistence = max(0.001, float(self.persistence))
        self.lacunarity = max(0.001, float(self.lacunarity))
        self.valley_power = max(0.25, float(self.valley_power))
        self.warp_strength = max(0.0, float(self.warp_strength))
        self.warp_frequency = max(0.001, float(self.warp_frequency))

    @property
    def name(self) -> str:
        return LAYER_KIND_NAMES[self.kind]

    def summary(self) -> str:
        warp = f", warp={self.warp_strength:.3f}" if self.warp_strength > 0.0 else ""
        state = "" if self.enabled else " off"
        return (
            f"{self.name}{state}: oct={self.octaves}, "
            f"freq={self.frequency:.2f}, amp={self.amplitude:.3f}{warp}"
        )


@dataclass
class TerrainStack:
    layers: list[TerrainLayer] = field(default_factory=list)

    @classmethod
    def default(cls) -> TerrainStack:
        return cls(
            [
                TerrainLayer(
                    kind=LayerKind.SIMPLE,
                    octaves=1,
                    frequency=6.0,
                    amplitude=0.08,
                    seed_x=12.7,
                    seed_y=-31.4,
                )
            ]
        )

    def reset_default(self) -> None:
        self.layers[:] = TerrainStack.default().layers

    def add_layer(self, layer: TerrainLayer) -> int:
        if len(self.layers) >= MAX_LAYERS:
            return len(self.layers) - 1
        self.layers.append(layer)
        return len(self.layers) - 1

    def add_random_layer(
        self,
        rng: random.Random | None = None,
        force_kind: LayerKind | None = None,
        octaves: int | None = None,
    ) -> int:
        rng = rng or random.Random()
        if force_kind is None:
            kind = rng.choice(
                [
                    LayerKind.SIMPLE,
                    LayerKind.RIDGED,
                    LayerKind.BILLOW,
                    LayerKind.VALLEY,
                    LayerKind.WARPED,
                ]
            )
        else:
            kind = force_kind
        kind = LayerKind(kind)
        selected_octaves = rng.randint(1, MAX_OCTAVES)
        if octaves is not None:
            selected_octaves = octaves

        amplitude = rng.uniform(0.018, 0.085)
        if kind == LayerKind.VALLEY:
            amplitude = rng.uniform(0.025, 0.075)
        if kind == LayerKind.WARPED:
            amplitude = rng.uniform(0.025, 0.09)

        warp_strength = 0.0
        if kind == LayerKind.WARPED:
            warp_strength = rng.uniform(0.025, 0.11)
        elif rng.random() < 0.18:
            warp_strength = rng.uniform(0.012, 0.045)

        layer = TerrainLayer(
            kind=kind,
            octaves=selected_octaves,
            frequency=rng.uniform(2.5, 18.0),
            amplitude=amplitude,
            persistence=rng.uniform(0.42, 0.62),
            lacunarity=rng.uniform(1.85, 2.35),
            seed_x=rng.uniform(-400.0, 400.0),
            seed_y=rng.uniform(-400.0, 400.0),
            rotation=rng.uniform(0.0, math.tau),
            valley_power=rng.uniform(1.6, 3.8),
            warp_strength=warp_strength,
            warp_frequency=rng.uniform(2.0, 10.0),
            warp_seed_x=rng.uniform(-700.0, 700.0),
            warp_seed_y=rng.uniform(-700.0, 700.0),
        )
        return self.add_layer(layer)

    def remove_layer(self, index: int) -> int:
        if not self.layers:
            return 0
        index = max(0, min(index, len(self.layers) - 1))
        del self.layers[index]
        if not self.layers:
            return 0
        return min(index, len(self.layers) - 1)

    def clamp_index(self, index: int) -> int:
        if not self.layers:
            return 0
        return max(0, min(index, len(self.layers) - 1))

    def height_color_scale(self) -> float:
        total = sum(abs(layer.amplitude) for layer in self.layers if layer.enabled)
        return max(total, 0.001)

    def describe(self) -> str:
        if not self.layers:
            return "empty terrain stack"
        return "\n".join(
            f"{idx:02d}. {layer.summary()}" for idx, layer in enumerate(self.layers)
        )

    def pack_gpu(self, max_layers: int = MAX_LAYERS) -> dict[str, np.ndarray | int]:
        count = min(len(self.layers), max_layers)
        types = np.zeros(max_layers, dtype=np.int32)
        octaves = np.ones(max_layers, dtype=np.int32)
        enabled = np.zeros(max_layers, dtype=np.int32)
        params0 = np.zeros((max_layers, 4), dtype="f4")
        params1 = np.zeros((max_layers, 4), dtype="f4")
        params2 = np.zeros((max_layers, 4), dtype="f4")

        for idx, layer in enumerate(self.layers[:count]):
            types[idx] = int(layer.kind)
            octaves[idx] = int(layer.octaves)
            enabled[idx] = 1 if layer.enabled else 0
            params0[idx] = (
                layer.frequency,
                layer.amplitude,
                layer.persistence,
                layer.lacunarity,
            )
            params1[idx] = (
                layer.seed_x,
                layer.seed_y,
                layer.rotation,
                layer.valley_power,
            )
            params2[idx] = (
                layer.warp_strength,
                layer.warp_frequency,
                layer.warp_seed_x,
                layer.warp_seed_y,
            )

        return {
            "count": count,
            "types": types,
            "octaves": octaves,
            "enabled": enabled,
            "params0": params0,
            "params1": params1,
            "params2": params2,
        }


def _fract(value: np.ndarray) -> np.ndarray:
    return value - np.floor(value)


def _fade(value: np.ndarray) -> np.ndarray:
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def _lerp(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    return a + (b - a) * t


def _hash2(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    p3x = _fract(x * 0.1031)
    p3y = _fract(y * 0.1031)
    p3z = _fract(x * 0.1031)
    dot_value = (
        p3x * (p3y + 33.33)
        + p3y * (p3z + 33.33)
        + p3z * (p3x + 33.33)
    )
    p3x = p3x + dot_value
    p3y = p3y + dot_value
    p3z = p3z + dot_value
    return _fract((p3x + p3y) * p3z)


def _gradient_dot(
    ix: np.ndarray,
    iy: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    seed: float,
) -> np.ndarray:
    angle = _hash2(ix + seed, iy + seed * 0.37) * math.tau
    gx = np.cos(angle)
    gy = np.sin(angle)
    return gx * (x - ix) + gy * (y - iy)


def gradient_noise_2d(x: np.ndarray, y: np.ndarray, seed: float = 0.0) -> np.ndarray:
    x0 = np.floor(x)
    y0 = np.floor(y)
    x1 = x0 + 1.0
    y1 = y0 + 1.0

    sx = _fade(x - x0)
    sy = _fade(y - y0)

    n00 = _gradient_dot(x0, y0, x, y, seed)
    n10 = _gradient_dot(x1, y0, x, y, seed)
    n01 = _gradient_dot(x0, y1, x, y, seed)
    n11 = _gradient_dot(x1, y1, x, y, seed)

    nx0 = _lerp(n00, n10, sx)
    nx1 = _lerp(n01, n11, sx)
    return np.clip(_lerp(nx0, nx1, sy) * 1.41421356237, -1.0, 1.0)


def _rotate_uv(
    x: np.ndarray,
    y: np.ndarray,
    rotation: float,
) -> tuple[np.ndarray, np.ndarray]:
    if abs(rotation) < 0.000001:
        return x, y
    c = math.cos(rotation)
    s = math.sin(rotation)
    cx = x - 0.5
    cy = y - 0.5
    return c * cx - s * cy + 0.5, s * cx + c * cy + 0.5


def _sample_base(layer: TerrainLayer, x: np.ndarray, y: np.ndarray, frequency: float, seed_shift: float) -> np.ndarray:
    seed = layer.seed_x * 0.13 + layer.seed_y * 0.17 + seed_shift
    return gradient_noise_2d(
        x * frequency + layer.seed_x,
        y * frequency + layer.seed_y,
        seed,
    )


def _sample_fbm(layer: TerrainLayer, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    total = np.zeros_like(x, dtype=np.float64)
    amp = 1.0
    freq = layer.frequency
    amp_sum = 0.0

    for octave in range(layer.octaves):
        total += _sample_base(layer, x, y, freq, float(octave) * 19.19) * amp
        amp_sum += amp
        freq *= layer.lacunarity
        amp *= layer.persistence

    if amp_sum <= 0.0:
        return total
    return total / amp_sum


def sample_layer(layer: TerrainLayer, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    rx, ry = _rotate_uv(x, y, layer.rotation)

    if layer.warp_strength > 0.0:
        wx = gradient_noise_2d(
            rx * layer.warp_frequency + layer.warp_seed_x,
            ry * layer.warp_frequency + layer.warp_seed_y,
            layer.warp_seed_x * 0.07 + 11.0,
        )
        wy = gradient_noise_2d(
            rx * layer.warp_frequency + layer.warp_seed_x + 37.2,
            ry * layer.warp_frequency + layer.warp_seed_y - 19.1,
            layer.warp_seed_y * 0.07 + 29.0,
        )
        rx = rx + wx * layer.warp_strength
        ry = ry + wy * layer.warp_strength

    if layer.kind == LayerKind.SIMPLE:
        if layer.octaves <= 1:
            value = _sample_base(layer, rx, ry, layer.frequency, 0.0)
        else:
            value = _sample_fbm(layer, rx, ry)
    elif layer.kind in (LayerKind.FBM, LayerKind.WARPED):
        value = _sample_fbm(layer, rx, ry)
    elif layer.kind == LayerKind.RIDGED:
        value = (1.0 - np.abs(_sample_fbm(layer, rx, ry))) * 2.0 - 1.0
    elif layer.kind == LayerKind.BILLOW:
        value = np.abs(_sample_fbm(layer, rx, ry)) * 2.0 - 1.0
    elif layer.kind == LayerKind.VALLEY:
        valley = np.maximum(0.0, 1.0 - np.abs(_sample_fbm(layer, rx, ry)))
        value = -np.power(valley, layer.valley_power)
    else:
        value = np.zeros_like(x, dtype=np.float64)

    return value * layer.amplitude


def compute_heightfield(
    stack: TerrainStack,
    resolution: int = 256,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    resolution = max(2, int(resolution))
    x = np.linspace(0.0, 1.0, resolution, dtype=np.float64)
    y = np.linspace(0.0, 1.0, resolution, dtype=np.float64)
    grid_x, grid_y = np.meshgrid(x, y)
    height = sample_stack(stack, grid_x, grid_y)
    return grid_x, grid_y, height


def sample_stack(stack: TerrainStack, grid_x: np.ndarray, grid_y: np.ndarray) -> np.ndarray:
    height = np.zeros_like(grid_x)

    for layer in stack.layers[:MAX_LAYERS]:
        if layer.enabled:
            height += sample_layer(layer, grid_x, grid_y)

    return height


def compute_terrain_vertex_data(
    stack: TerrainStack,
    resolution: int = 256,
) -> np.ndarray:
    grid_x, grid_y, height = compute_heightfield(stack, resolution)
    step = 1.0 / max(int(resolution) - 1, 1)
    height_x = sample_stack(stack, grid_x + step, grid_y)
    height_y = sample_stack(stack, grid_x, grid_y + step)

    normal_x = -((height_x - height) / step)
    normal_y = np.ones_like(height)
    normal_z = -((height_y - height) / step)
    normal_len = np.sqrt(normal_x * normal_x + normal_y * normal_y + normal_z * normal_z)
    normal_len = np.maximum(normal_len, 0.000001)

    positions = np.stack(
        [
            grid_x - 0.5,
            height,
            grid_y - 0.5,
        ],
        axis=-1,
    )
    normals = np.stack(
        [
            normal_x / normal_len,
            normal_y / normal_len,
            normal_z / normal_len,
        ],
        axis=-1,
    )
    vertex_data = np.concatenate([positions, normals, height[..., None]], axis=-1)
    return vertex_data.astype("f4").reshape(-1, 7)

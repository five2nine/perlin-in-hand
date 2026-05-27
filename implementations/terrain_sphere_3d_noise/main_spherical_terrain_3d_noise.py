from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import sys
import time
from typing import Any

import imgui
import moderngl
import moderngl_window as mglw
import numpy as np
from moderngl_window.integrations.imgui import ModernglWindowRenderer
from moderngl_window.scene import OrbitCamera


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
SHADER_DIR = PROJECT_ROOT / "implementations" / "terrain_generation_gpu" / "shaders"

with open(SHADER_DIR / "terrain_heightfield.vert", "r", encoding="utf-8") as f:
    RENDER_VERTEX_SHADER = f.read()

with open(SHADER_DIR / "terrain_heightfield.frag", "r", encoding="utf-8") as f:
    FRAGMENT_SHADER = f.read()


@dataclass(frozen=True)
class SphereTerrainConfig:
    subdivisions: int = 5
    frequency: float = 3.2
    amplitude: float = 0.12
    octaves: int = 5
    persistence: float = 0.52
    lacunarity: float = 2.03
    seed: float = 41.0


def parse_case_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Spherical terrain case using 3D noise sampled by direction vectors.",
        add_help=False,
    )
    parser.add_argument("--subdivisions", type=int, default=5)
    parser.add_argument("--frequency", type=float, default=3.2)
    parser.add_argument("--amplitude", type=float, default=0.12)
    parser.add_argument("--octaves", type=int, default=5)
    parser.add_argument("--seed", type=float, default=41.0)
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--help-case", action="store_true")

    args = argparse.Namespace(
        subdivisions=5,
        frequency=3.2,
        amplitude=0.12,
        octaves=5,
        seed=41.0,
        analyze_only=False,
        help_case=False,
    )
    remaining: list[str] = []
    case_value_options = {
        "--subdivisions",
        "--frequency",
        "--amplitude",
        "--octaves",
        "--seed",
    }
    mglw_value_options = {
        "-wnd",
        "--window",
        "-vs",
        "--vsync",
        "-r",
        "--resizable",
        "-hd",
        "--hidden",
        "-s",
        "--samples",
        "-c",
        "--cursor",
        "--size",
        "--size_mult",
        "--backend",
    }
    mglw_flag_options = {"-fs", "--fullscreen", "-h", "--help"}

    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--help-case":
            args.help_case = True
            index += 1
        elif token == "--analyze-only":
            args.analyze_only = True
            index += 1
        elif token in case_value_options:
            if index + 1 >= len(argv):
                parser.error(f"{token} requires a value")
            setattr(args, token[2:].replace("-", "_"), _parse_case_value(token, argv[index + 1]))
            index += 2
        elif any(token.startswith(option + "=") for option in case_value_options):
            name, value = token.split("=", 1)
            setattr(args, name[2:].replace("-", "_"), _parse_case_value(name, value))
            index += 1
        elif token in mglw_value_options:
            remaining.append(token)
            if index + 1 >= len(argv):
                parser.error(f"{token} requires a value")
            remaining.append(argv[index + 1])
            index += 2
        elif token in mglw_flag_options:
            remaining.append(token)
            index += 1
        else:
            remaining.append(token)
            index += 1

    if args.help_case:
        parser.print_help()
        raise SystemExit(0)
    return args, remaining


def _parse_case_value(option: str, value: str) -> int | float:
    if option in {"--subdivisions", "--octaves"}:
        return int(value)
    return float(value)


CASE_ARGS, MGLW_ARGS = parse_case_args(sys.argv[1:])


def _normalize(vectors: np.ndarray) -> np.ndarray:
    length = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.maximum(length, 1e-12)


def make_icosahedron() -> tuple[np.ndarray, np.ndarray]:
    phi = (1.0 + math.sqrt(5.0)) * 0.5
    vertices = np.array(
        [
            (-1, phi, 0),
            (1, phi, 0),
            (-1, -phi, 0),
            (1, -phi, 0),
            (0, -1, phi),
            (0, 1, phi),
            (0, -1, -phi),
            (0, 1, -phi),
            (phi, 0, -1),
            (phi, 0, 1),
            (-phi, 0, -1),
            (-phi, 0, 1),
        ],
        dtype=np.float64,
    )
    faces = np.array(
        [
            (0, 11, 5),
            (0, 5, 1),
            (0, 1, 7),
            (0, 7, 10),
            (0, 10, 11),
            (1, 5, 9),
            (5, 11, 4),
            (11, 10, 2),
            (10, 7, 6),
            (7, 1, 8),
            (3, 9, 4),
            (3, 4, 2),
            (3, 2, 6),
            (3, 6, 8),
            (3, 8, 9),
            (4, 9, 5),
            (2, 4, 11),
            (6, 2, 10),
            (8, 6, 7),
            (9, 8, 1),
        ],
        dtype=np.uint32,
    )
    return _normalize(vertices), faces


def make_icosphere(subdivisions: int) -> tuple[np.ndarray, np.ndarray]:
    subdivisions = max(0, min(7, int(subdivisions)))
    vertices, faces = make_icosahedron()
    vertex_list = [vertex for vertex in vertices]
    face_list = [tuple(int(index) for index in face) for face in faces]

    for _ in range(subdivisions):
        midpoint_cache: dict[tuple[int, int], int] = {}
        next_faces: list[tuple[int, int, int]] = []

        def midpoint_index(a: int, b: int) -> int:
            key = (a, b) if a < b else (b, a)
            if key in midpoint_cache:
                return midpoint_cache[key]
            midpoint = _normalize((vertex_list[a] + vertex_list[b]).reshape(1, 3))[0]
            vertex_list.append(midpoint)
            index = len(vertex_list) - 1
            midpoint_cache[key] = index
            return index

        for a, b, c in face_list:
            ab = midpoint_index(a, b)
            bc = midpoint_index(b, c)
            ca = midpoint_index(c, a)
            next_faces.extend(
                [
                    (a, ab, ca),
                    (b, bc, ab),
                    (c, ca, bc),
                    (ab, bc, ca),
                ]
            )
        face_list = next_faces

    return np.asarray(vertex_list, dtype=np.float64), np.asarray(face_list, dtype=np.uint32)


def _fract(value: np.ndarray) -> np.ndarray:
    return value - np.floor(value)


def _fade(value: np.ndarray) -> np.ndarray:
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def _lerp(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    return a + (b - a) * t


def _hash3(x: np.ndarray, y: np.ndarray, z: np.ndarray, salt: float) -> np.ndarray:
    value = np.sin(x * 127.1 + y * 311.7 + z * 74.7 + salt * 269.5)
    return _fract(value * 43758.5453123)


def _gradient_dot(
    ix: np.ndarray,
    iy: np.ndarray,
    iz: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    seed: float,
) -> np.ndarray:
    h0 = _hash3(ix, iy, iz, seed)
    h1 = _hash3(ix, iy, iz, seed + 17.0)
    gz = h0 * 2.0 - 1.0
    radius = np.sqrt(np.maximum(1.0 - gz * gz, 0.0))
    angle = h1 * math.tau
    gx = np.cos(angle) * radius
    gy = np.sin(angle) * radius
    return gx * (x - ix) + gy * (y - iy) + gz * (z - iz)


def gradient_noise_3d(points: np.ndarray, seed: float = 0.0) -> np.ndarray:
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    x0 = np.floor(x)
    y0 = np.floor(y)
    z0 = np.floor(z)
    x1 = x0 + 1.0
    y1 = y0 + 1.0
    z1 = z0 + 1.0

    sx = _fade(x - x0)
    sy = _fade(y - y0)
    sz = _fade(z - z0)

    n000 = _gradient_dot(x0, y0, z0, x, y, z, seed)
    n100 = _gradient_dot(x1, y0, z0, x, y, z, seed)
    n010 = _gradient_dot(x0, y1, z0, x, y, z, seed)
    n110 = _gradient_dot(x1, y1, z0, x, y, z, seed)
    n001 = _gradient_dot(x0, y0, z1, x, y, z, seed)
    n101 = _gradient_dot(x1, y0, z1, x, y, z, seed)
    n011 = _gradient_dot(x0, y1, z1, x, y, z, seed)
    n111 = _gradient_dot(x1, y1, z1, x, y, z, seed)

    nx00 = _lerp(n000, n100, sx)
    nx10 = _lerp(n010, n110, sx)
    nx01 = _lerp(n001, n101, sx)
    nx11 = _lerp(n011, n111, sx)
    nxy0 = _lerp(nx00, nx10, sy)
    nxy1 = _lerp(nx01, nx11, sy)
    return np.clip(_lerp(nxy0, nxy1, sz) * 1.73205080757, -1.0, 1.0)


def sample_fbm_3d(directions: np.ndarray, config: SphereTerrainConfig) -> np.ndarray:
    total = np.zeros(directions.shape[0], dtype=np.float64)
    amplitude = 1.0
    frequency = float(config.frequency)
    amplitude_sum = 0.0

    for octave in range(max(1, int(config.octaves))):
        points = directions * frequency + np.array(
            [config.seed * 0.11, config.seed * -0.07, config.seed * 0.19],
            dtype=np.float64,
        )
        total += gradient_noise_3d(points, config.seed + octave * 23.31) * amplitude
        amplitude_sum += amplitude
        frequency *= config.lacunarity
        amplitude *= config.persistence

    return total / max(amplitude_sum, 1e-8) * config.amplitude


def compute_vertex_normals(positions: np.ndarray, faces: np.ndarray) -> np.ndarray:
    triangles = positions[faces]
    face_normals = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    face_normals = _normalize(face_normals)
    face_centers = np.mean(triangles, axis=1)
    inward = np.sum(face_normals * face_centers, axis=1) < 0.0
    face_normals[inward] *= -1.0

    normals = np.zeros_like(positions)
    np.add.at(normals, faces[:, 0], face_normals)
    np.add.at(normals, faces[:, 1], face_normals)
    np.add.at(normals, faces[:, 2], face_normals)
    return _normalize(normals)


def build_spherical_terrain(config: SphereTerrainConfig) -> dict[str, Any]:
    directions, faces = make_icosphere(config.subdivisions)
    heights = sample_fbm_3d(directions, config)
    positions = directions * (1.0 + heights[:, None])
    normals = compute_vertex_normals(positions, faces)
    vertices = np.concatenate([positions, normals, heights[:, None]], axis=1).astype("f4")
    indices_tri = faces.astype("u4")
    stats = compute_latitude_stats(directions, heights)
    return {
        "directions": directions.astype("f4"),
        "positions": positions.astype("f4"),
        "normals": normals.astype("f4"),
        "heights": heights.astype("f4"),
        "vertices": vertices,
        "indices_tri": indices_tri,
        "indices": indices_tri.reshape(-1),
        "stats": stats,
        "height_min": float(np.min(heights)),
        "height_max": float(np.max(heights)),
        "height_scale": max(float(np.max(np.abs(heights))), 0.001),
    }


def compute_latitude_stats(directions: np.ndarray, heights: np.ndarray) -> list[dict[str, float | int | str]]:
    lat = np.degrees(np.arcsin(np.clip(directions[:, 1], -1.0, 1.0)))
    bands = [
        ("south polar", -90.0, -60.0),
        ("south mid", -60.0, -30.0),
        ("equatorial", -30.0, 30.0),
        ("north mid", 30.0, 60.0),
        ("north polar", 60.0, 90.0),
    ]
    results: list[dict[str, float | int | str]] = []
    for name, low, high in bands:
        if high == 90.0:
            mask = (lat >= low) & (lat <= high)
        else:
            mask = (lat >= low) & (lat < high)
        values = heights[mask]
        results.append(
            {
                "name": name,
                "count": int(values.size),
                "mean": float(np.mean(values)) if values.size else 0.0,
                "std": float(np.std(values)) if values.size else 0.0,
                "min": float(np.min(values)) if values.size else 0.0,
                "max": float(np.max(values)) if values.size else 0.0,
            }
        )
    return results


class SphereTerrainPanel:
    def __init__(self, window: Any) -> None:
        imgui.create_context()
        io = imgui.get_io()
        io.ini_file_name = None
        style = imgui.get_style()
        style.window_rounding = 5.0
        style.frame_rounding = 4.0
        style.grab_rounding = 4.0

        self.window = window
        self.renderer = ModernglWindowRenderer(window)
        self.io = imgui.get_io()
        self.panel_width = 420.0
        self.panel_height = 560.0

    @property
    def wants_mouse(self) -> bool:
        return bool(self.io.want_capture_mouse)

    def render(self, app: Any) -> None:
        self._sync_display_state()
        imgui.new_frame()
        self._draw_panel(app)
        imgui.render()
        self.renderer.render(imgui.get_draw_data())

    def shutdown(self) -> None:
        self.renderer.shutdown()

    def resize(self, width: int, height: int) -> None:
        self.renderer.resize(width, height)
        self._sync_display_state()

    def key_event(self, key: Any, action: Any, modifiers: Any) -> None:
        self.renderer.key_event(key, action, modifiers)

    def mouse_position_event(self, x: int, y: int, dx: int, dy: int) -> None:
        self._set_mouse_pos(x, y)

    def mouse_drag_event(self, x: int, y: int, dx: int, dy: int) -> None:
        self._set_mouse_pos(x, y)

    def mouse_scroll_event(self, x_offset: float, y_offset: float) -> None:
        self.io.mouse_wheel_horizontal += float(x_offset)
        self.io.mouse_wheel += float(y_offset)

    def mouse_press_event(self, x: int, y: int, button: int) -> None:
        self._set_mouse_pos(x, y)
        self._set_mouse_button(button, True)

    def mouse_release_event(self, x: int, y: int, button: int) -> None:
        self._set_mouse_pos(x, y)
        self._set_mouse_button(button, False)

    def unicode_char_entered(self, char: str) -> None:
        self.renderer.unicode_char_entered(char)

    def _sync_display_state(self) -> None:
        width, height = self.window.size
        buffer_width, buffer_height = self.window.buffer_size
        self.io.display_size = (width, height)
        self.io.display_fb_scale = (
            buffer_width / max(width, 1),
            buffer_height / max(height, 1),
        )
        margin = 16.0
        self.panel_width = min(420.0, max(160.0, float(width) - margin * 2.0))
        self.panel_height = min(620.0, max(180.0, float(height) - margin * 2.0))

    def _set_mouse_pos(self, x: int, y: int) -> None:
        viewport_x = x - (
            self.window.width - self.window.viewport_width / self.window.pixel_ratio
        ) / 2
        viewport_y = y - (
            self.window.height - self.window.viewport_height / self.window.pixel_ratio
        ) / 2
        self.io.mouse_pos = (float(viewport_x), float(viewport_y))

    def _set_mouse_button(self, button: int, pressed: bool) -> None:
        if button == self.window.mouse.left:
            self.io.mouse_down[0] = pressed
        elif button == self.window.mouse.middle:
            self.io.mouse_down[2] = pressed
        elif button == self.window.mouse.right:
            self.io.mouse_down[1] = pressed

    def _draw_panel(self, app: Any) -> None:
        imgui.set_next_window_position(16, 16, condition=imgui.FIRST_USE_EVER)
        imgui.set_next_window_size(
            self.panel_width,
            self.panel_height,
            condition=imgui.FIRST_USE_EVER,
        )
        expanded, _ = imgui.begin("Spherical Terrain")
        if expanded:
            imgui.text("3D noise sampled by sphere direction")
            imgui.text(f"FPS: {app.fps_val:.1f}")
            imgui.separator()

            changed = False
            changed_subdivisions, subdivisions = imgui.slider_int(
                "Subdivisions",
                app.config.subdivisions,
                1,
                6,
            )
            changed_frequency, frequency = imgui.slider_float(
                "Frequency",
                app.config.frequency,
                0.5,
                14.0,
                format="%.2f",
            )
            changed_amplitude, amplitude = imgui.slider_float(
                "Amplitude",
                app.config.amplitude,
                0.0,
                0.35,
                format="%.3f",
            )
            changed_octaves, octaves = imgui.slider_int("Octaves", app.config.octaves, 1, 6)
            changed_seed, seed = imgui.slider_float(
                "Seed",
                app.config.seed,
                -200.0,
                200.0,
                format="%.2f",
            )
            changed = any(
                [
                    changed_subdivisions,
                    changed_frequency,
                    changed_amplitude,
                    changed_octaves,
                    changed_seed,
                ]
            )
            if changed:
                app.config = SphereTerrainConfig(
                    subdivisions=int(subdivisions),
                    frequency=float(frequency),
                    amplitude=float(amplitude),
                    octaves=int(octaves),
                    seed=float(seed),
                    persistence=app.config.persistence,
                    lacunarity=app.config.lacunarity,
                )
                app.rebuild_mesh()

            changed_palette, palette = imgui.combo(
                "Palette",
                app.palette,
                app.palette_names,
            )
            if changed_palette:
                app.palette = palette

            changed_wireframe, wireframe = imgui.checkbox("Wireframe", app.wireframe)
            if changed_wireframe:
                app.wireframe = wireframe

            if imgui.button("Reset Camera"):
                app.reset_camera()

            imgui.separator()
            imgui.text(f"Vertices: {app.mesh['vertices'].shape[0]:,}")
            imgui.text(f"Triangles: {app.mesh['indices_tri'].shape[0]:,}")
            imgui.text(
                f"Height: {app.mesh['height_min']:.6f} .. {app.mesh['height_max']:.6f}"
            )
            imgui.separator()
            imgui.text("Latitude bands")
            for stat in app.mesh["stats"]:
                imgui.text(
                    f"{stat['name']}: n={stat['count']}, "
                    f"std={stat['std']:.5f}, mean={stat['mean']:.5f}"
                )
            imgui.separator()
            imgui.text("Mouse drag rotate | Wheel zoom | C palette | W wire")
        imgui.end()


class SphericalTerrain3DNoiseApp(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "Spherical Terrain - 3D Noise Sampling"
    window_size = (1920, 1080)
    aspect_ratio = None
    resizable = True
    vsync = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.render_prog = self.ctx.program(
            vertex_shader=RENDER_VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER,
        )

        self.camera = OrbitCamera(
            target=(0.0, 0.0, 0.0),
            radius=3.0,
            angles=(35.0, -35.0),
            aspect_ratio=self.wnd.aspect_ratio,
            near=0.01,
            far=100.0,
        )
        self.camera.projection.update(fov=45.0)
        self.camera.zoom_sensitivity = 0.08

        self.config = SphereTerrainConfig(
            subdivisions=CASE_ARGS.subdivisions,
            frequency=CASE_ARGS.frequency,
            amplitude=CASE_ARGS.amplitude,
            octaves=CASE_ARGS.octaves,
            seed=CASE_ARGS.seed,
        )
        self.palette_names = ["Geology", "Topographic", "Ink"]
        self.palette = 1
        self.wireframe = False
        self.model_matrix = np.eye(4, dtype="f4")
        self.model_matrix_bytes = self.model_matrix.tobytes()
        self.mesh: dict[str, Any] = {}
        self.terrain_vbo = None
        self.ebo = None
        self.render_vao = None
        self.rebuild_mesh()

        self.fps_timer = 0.0
        self.frame_count = 0
        self.last_time = time.perf_counter()
        self.target_fps = 60
        self.fps_val = 0.0
        self.ui = SphereTerrainPanel(self.wnd)

        print("=" * 72)
        print("Spherical Terrain - 3D Noise Sampling")
        print("-" * 72)
        print("Controls: mouse drag rotate, wheel zoom, C palette, W wireframe, HOME reset")
        print("Use --analyze-only to print latitude-band statistics without opening a window.")
        print("=" * 72)

    def rebuild_mesh(self) -> None:
        self.mesh = build_spherical_terrain(self.config)
        if self.terrain_vbo is not None:
            self.terrain_vbo.release()
        if self.ebo is not None:
            self.ebo.release()
        if self.render_vao is not None:
            self.render_vao.release()

        self.terrain_vbo = self.ctx.buffer(self.mesh["vertices"].tobytes())
        self.ebo = self.ctx.buffer(self.mesh["indices"].astype("u4").tobytes())
        self.render_vao = self.ctx.vertex_array(
            self.render_prog,
            [(self.terrain_vbo, "3f 3f 1f", "in_pos", "in_normal", "in_height")],
            index_buffer=self.ebo,
            index_element_size=4,
        )
        self.wnd.title = (
            "Spherical Terrain | "
            f"subdiv={self.config.subdivisions} | "
            f"verts={self.mesh['vertices'].shape[0]:,}"
        )

    def reset_camera(self) -> None:
        self.camera.radius = 3.0
        self.camera.angle_x = 35.0
        self.camera.angle_y = -35.0

    def on_render(self, time_since_start: float, frametime: float):
        now = time.perf_counter()
        elapsed = now - self.last_time
        target_time = 1.0 / self.target_fps
        if elapsed < target_time:
            time.sleep(target_time - elapsed)
            now = time.perf_counter()
        self.last_time = now

        self.ctx.clear(0.045, 0.048, 0.052, 1.0)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)
        self.ctx.wireframe = self.wireframe

        self.render_prog["m_proj"].write(self.camera.projection.matrix)
        self.render_prog["m_view"].write(self.camera.matrix)
        self.render_prog["m_model"].write(self.model_matrix_bytes)
        self.render_prog["u_palette"].value = int(self.palette)
        self.render_prog["u_light_pos"].value = (-1.8, 2.4, 2.0)
        self.render_prog["u_height_color_scale"].value = float(self.mesh["height_scale"])

        try:
            view_pos = tuple(self.camera.position)
        except (TypeError, AttributeError):
            view_pos = (
                self.camera.position[0],
                self.camera.position[1],
                self.camera.position[2],
            )
        self.render_prog["u_view_pos"].value = view_pos
        self.render_vao.render(moderngl.TRIANGLES)
        self.ctx.wireframe = False

        self.fps_timer += frametime
        self.frame_count += 1
        if self.fps_timer >= 0.5:
            self.fps_val = self.frame_count / self.fps_timer
            self.fps_timer = 0.0
            self.frame_count = 0

        self.ui.render(self)

    def on_key_event(self, key, action, modifiers):
        self.ui.key_event(key, action, modifiers)
        if action != self.wnd.keys.ACTION_PRESS:
            return
        if key == self.wnd.keys.C:
            self.palette = (self.palette + 1) % len(self.palette_names)
        elif key == self.wnd.keys.W:
            self.wireframe = not self.wireframe
        elif key == self.wnd.keys.HOME:
            self.reset_camera()

    def on_mouse_drag_event(self, x, y, dx, dy):
        self.ui.mouse_drag_event(x, y, dx, dy)
        if self.ui.wants_mouse:
            return
        if abs(dx) > 100 or abs(dy) > 100:
            return
        self.camera.angle_x += dx * self.camera.mouse_sensitivity / 10.0
        self.camera.angle_y += dy * self.camera.mouse_sensitivity / 10.0
        self.camera.angle_y = max(min(self.camera.angle_y, -5.0), -175.0)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        self.ui.mouse_scroll_event(x_offset, y_offset)
        if self.ui.wants_mouse:
            return
        self.camera.radius = max(0.4, self.camera.radius - y_offset * self.camera.zoom_sensitivity)

    def on_mouse_position_event(self, x, y, dx, dy):
        self.ui.mouse_position_event(x, y, dx, dy)

    def on_mouse_press_event(self, x, y, button):
        self.ui.mouse_press_event(x, y, button)

    def on_mouse_release_event(self, x, y, button):
        self.ui.mouse_release_event(x, y, button)

    def on_unicode_char_entered(self, char):
        self.ui.unicode_char_entered(char)

    def on_resize(self, width: int, height: int):
        self.ctx.viewport = (0, 0, width, height)
        aspect = width / height if height > 0 else 1.0
        self.camera.projection.update(aspect_ratio=aspect)
        if hasattr(self, "ui"):
            self.ui.resize(width, height)

    def on_close(self):
        if hasattr(self, "ui"):
            self.ui.shutdown()


def print_analysis() -> None:
    config = SphereTerrainConfig(
        subdivisions=CASE_ARGS.subdivisions,
        frequency=CASE_ARGS.frequency,
        amplitude=CASE_ARGS.amplitude,
        octaves=CASE_ARGS.octaves,
        seed=CASE_ARGS.seed,
    )
    mesh = build_spherical_terrain(config)
    print("Spherical Terrain - 3D Noise Sampling")
    print(f"subdivisions: {config.subdivisions}")
    print(f"vertices: {mesh['vertices'].shape[0]}")
    print(f"triangles: {mesh['indices_tri'].shape[0]}")
    print(f"frequency: {config.frequency}")
    print(f"amplitude: {config.amplitude}")
    print(f"octaves: {config.octaves}")
    print(f"seed: {config.seed}")
    print(f"height: {mesh['height_min']:.8f} .. {mesh['height_max']:.8f}")
    print("latitude bands:")
    for stat in mesh["stats"]:
        print(
            f"  {stat['name']:12s} "
            f"n={stat['count']:5d} "
            f"mean={stat['mean']:+.8f} "
            f"std={stat['std']:.8f} "
            f"range={stat['min']:+.8f}..{stat['max']:+.8f}"
        )


def main() -> None:
    if CASE_ARGS.analyze_only:
        print_analysis()
        return
    mglw.run_window_config(
        SphericalTerrain3DNoiseApp,
        args=MGLW_ARGS if MGLW_ARGS else ["--size_mult", "1"],
    )


if __name__ == "__main__":
    main()

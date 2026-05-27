# GPU viewer for exported static terrain .npz meshes.

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
GPU_TERRAIN_DIR = PROJECT_ROOT / "implementations" / "terrain_gpu_generator_plane"
COMMON_DIR = PROJECT_ROOT / "implementations" / "terrain_gpu_runtime_common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from terrain_npz_loader import DEFAULT_EXPORT_DIR, load_exported_mesh, newest_export  # noqa: E402


with open(
    GPU_TERRAIN_DIR / "shaders" / "terrain_heightfield.vert",
    "r",
    encoding="utf-8",
) as f:
    RENDER_VERTEX_SHADER = f.read()

with open(
    GPU_TERRAIN_DIR / "shaders" / "terrain_heightfield.frag",
    "r",
    encoding="utf-8",
) as f:
    FRAGMENT_SHADER = f.read()


def parse_viewer_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="GPU viewer for exported terrain_generation .npz meshes.",
        add_help=False,
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to an exported terrain .npz file. Defaults to the newest CPU/GPU export.",
    )
    parser.add_argument(
        "--palette",
        choices=("geology", "topographic", "ink"),
        default=None,
        help="Initial color palette override.",
    )
    parser.add_argument(
        "--help-viewer",
        action="store_true",
        help="Show GPU viewer options and exit.",
    )
    args = argparse.Namespace(path=None, palette=None, help_viewer=False)
    remaining: list[str] = []
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
        if token == "--help-viewer":
            args.help_viewer = True
            index += 1
        elif token == "--palette":
            if index + 1 >= len(argv):
                parser.error("--palette requires a value")
            args.palette = argv[index + 1]
            index += 2
        elif token.startswith("--palette="):
            args.palette = token.split("=", 1)[1]
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
        elif token.startswith("-"):
            remaining.append(token)
            index += 1
        elif args.path is None:
            args.path = token
            index += 1
        else:
            remaining.append(token)
            index += 1

    if args.help_viewer:
        parser.print_help()
        raise SystemExit(0)
    if args.palette not in (None, "geology", "topographic", "ink"):
        parser.error("--palette must be one of: geology, topographic, ink")
    return args, remaining


VIEWER_ARGS, MGLW_ARGS = parse_viewer_args(sys.argv[1:])
PLANE_LIGHT_POS = (-0.35, 1.3, 0.45)
SPHERE_LIGHT_POS = (-1.8, 2.4, 2.0)


@dataclass(frozen=True)
class GizmoProjection:
    x: float
    y: float
    depth: float


def direction_from_lon_lat(lon_deg: float, lat_deg: float) -> np.ndarray:
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    cos_lat = math.cos(lat)
    return np.array(
        [
            cos_lat * math.cos(lon),
            math.sin(lat),
            cos_lat * math.sin(lon),
        ],
        dtype=np.float64,
    )


def lon_lat_from_direction(direction: np.ndarray) -> tuple[float, float]:
    normal = direction / max(float(np.linalg.norm(direction)), 1e-12)
    lon = math.degrees(math.atan2(float(normal[2]), float(normal[0])))
    lat = math.degrees(math.asin(max(-1.0, min(1.0, float(normal[1])))))
    return lon, lat


def list_exported_npz_files(current_path: Path | None = None) -> list[Path]:
    search_dirs = [DEFAULT_EXPORT_DIR]
    if current_path is not None:
        search_dirs.append(Path(current_path).resolve().parent)

    seen: set[Path] = set()
    files: list[Path] = []
    for directory in search_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.npz"), key=lambda item: item.stat().st_mtime, reverse=True):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)

    if current_path is not None:
        resolved_current = Path(current_path).resolve()
        if resolved_current.exists() and resolved_current not in seen:
            files.insert(0, resolved_current)

    app_exports = [
        path
        for path in files
        if path.name.startswith(("terrain_cpu_", "terrain_gpu_", "terrain_sphere_"))
    ]
    other_exports = [path for path in files if path not in app_exports]
    return app_exports + other_exports


class TerrainNpzInfoPanel:
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
        self.panel_width = 430.0
        self.panel_height = 440.0

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
        self.panel_width = min(430.0, max(160.0, float(width) - margin * 2.0))
        self.panel_height = min(460.0, max(180.0, float(height) - margin * 2.0))

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
        expanded, _ = imgui.begin("Loaded Terrain")
        if expanded:
            imgui.text("File")
            imgui.text_wrapped(str(app.export_path))
            imgui.separator()
            if app.metadata.get("generator_type") == "sphere_terrain":
                imgui.text(f"Mesh: {app.metadata.get('topology', 'mesh')}")
            else:
                imgui.text(f"Grid: {app.rows} x {app.cols}")
            imgui.text(f"Vertices: {app.mesh['vertices'].shape[0]:,}")
            imgui.text(f"Triangles: {app.mesh['indices'].shape[0] // 3:,}")
            imgui.text(
                f"Height: {app.mesh['height_min']:.6f} .. {app.mesh['height_max']:.6f}"
            )
            imgui.text(f"Backend: {app.metadata.get('backend', 'unknown')}")
            imgui.text(f"Layers: {app.metadata.get('layer_count', 'unknown')}")
            imgui.text(f"Palette: {app.palette_names[app.palette]}")
            imgui.text(f"Light: {app.light_label()}")
            imgui.text(f"FPS: {app.fps_val:.1f}")
            imgui.separator()
            self._draw_loading_menu(app)
            imgui.separator()
            imgui.text("Mouse drag rotate | Wheel zoom | C palette | HOME reset")
        imgui.end()
        if app.is_sphere_terrain():
            self._draw_orientation_gizmo(app)

    def _draw_loading_menu(self, app: Any) -> None:
        imgui.text("Load Model")
        if not app.export_files:
            imgui.text_wrapped("No exported .npz files found.")
        else:
            labels = [app.export_label(path) for path in app.export_files]
            changed, selected = imgui.combo(
                "Export##export_load_combo",
                app.selected_export_index,
                labels,
            )
            if changed:
                app.selected_export_index = selected

            if imgui.button("Load Selected"):
                app.load_selected_export()
            imgui.same_line()
            if imgui.button("Reload"):
                app.reload_current_export()

            if imgui.button("Prev"):
                app.load_export_delta(-1)
            imgui.same_line()
            if imgui.button("Next"):
                app.load_export_delta(1)
            imgui.same_line()
            if imgui.button("Refresh"):
                app.refresh_export_files()

            _, app.use_file_palette_on_load = imgui.checkbox(
                "Use file palette",
                app.use_file_palette_on_load,
            )
            _, app.reset_camera_on_load = imgui.checkbox(
                "Reset camera on load",
                app.reset_camera_on_load,
            )

        if app.load_status:
            imgui.text_wrapped(app.load_status)

    def _draw_orientation_gizmo(self, app: Any) -> None:
        width, _height = self.window.size
        size = 188.0
        margin = 18.0
        center_x = float(width) - margin - size * 0.5
        center_y = margin + size * 0.5
        radius = size * 0.32

        draw_list = imgui.get_foreground_draw_list()
        color_panel = imgui.get_color_u32_rgba(0.03, 0.035, 0.04, 0.68)
        color_outline = imgui.get_color_u32_rgba(0.82, 0.86, 0.82, 0.78)
        color_back = imgui.get_color_u32_rgba(0.38, 0.43, 0.45, 0.48)
        color_equator = imgui.get_color_u32_rgba(0.42, 0.66, 0.72, 0.58)
        color_lon0 = imgui.get_color_u32_rgba(0.95, 0.72, 0.28, 0.92)
        color_lon90 = imgui.get_color_u32_rgba(0.38, 0.78, 0.95, 0.92)
        color_lon_neg90 = imgui.get_color_u32_rgba(0.95, 0.46, 0.46, 0.92)
        color_north = imgui.get_color_u32_rgba(0.94, 0.95, 0.88, 1.0)
        color_text = imgui.get_color_u32_rgba(0.90, 0.93, 0.90, 0.94)

        left = center_x - size * 0.5
        top = center_y - size * 0.5
        right = center_x + size * 0.5
        bottom = center_y + size * 0.5 + 22.0
        draw_list.add_rect_filled(left, top, right, bottom, color_panel, 8.0)
        draw_list.add_circle_filled(
            center_x,
            center_y,
            radius,
            imgui.get_color_u32_rgba(0.09, 0.12, 0.14, 0.82),
            48,
        )
        draw_list.add_circle(center_x, center_y, radius, color_outline, 64, 1.4)

        basis = self._camera_projection_basis(app)
        self._draw_gizmo_circle(
            draw_list,
            basis,
            center_x,
            center_y,
            radius,
            lambda t: direction_from_lon_lat(math.degrees(t), 0.0),
            color_equator,
            color_back,
            1.2,
            closed=True,
        )
        for lon, color in [(0.0, color_lon0), (90.0, color_lon90), (-90.0, color_lon_neg90)]:
            self._draw_gizmo_circle(
                draw_list,
                basis,
                center_x,
                center_y,
                radius,
                lambda t, lon=lon: direction_from_lon_lat(lon, math.degrees(t)),
                color,
                color_back,
                1.8,
                closed=False,
                t_min=-math.pi * 0.5,
                t_max=math.pi * 0.5,
            )

        markers = [
            ("N", np.array([0.0, 1.0, 0.0], dtype=np.float64), color_north),
            ("0", np.array([1.0, 0.0, 0.0], dtype=np.float64), color_lon0),
            ("+90", np.array([0.0, 0.0, 1.0], dtype=np.float64), color_lon90),
            ("-90", np.array([0.0, 0.0, -1.0], dtype=np.float64), color_lon_neg90),
        ]
        for label, direction, color in markers:
            point = self._project_direction(direction, basis, center_x, center_y, radius)
            marker_color = color if point.depth >= 0.0 else color_back
            marker_radius = 4.0 if label == "N" else 3.5
            draw_list.add_circle_filled(point.x, point.y, marker_radius, marker_color, 16)
            draw_list.add_text(point.x + 5.0, point.y - 7.0, marker_color, label)

        view_lon, view_lat = lon_lat_from_direction(np.asarray(app.camera.position, dtype=np.float64))
        draw_list.add_text(
            left + 10.0,
            bottom - 17.0,
            color_text,
            f"view {view_lon:+.1f}/{view_lat:+.1f}",
        )

    def _camera_projection_basis(
        self,
        app: Any,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        view_dir = np.asarray(app.camera.position, dtype=np.float64)
        view_dir = view_dir / max(float(np.linalg.norm(view_dir)), 1e-12)
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        right = np.cross(world_up, view_dir)
        if float(np.linalg.norm(right)) < 1e-6:
            right = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        else:
            right = right / float(np.linalg.norm(right))
        up = np.cross(view_dir, right)
        up = up / max(float(np.linalg.norm(up)), 1e-12)
        return right, up, view_dir

    def _project_direction(
        self,
        direction: np.ndarray,
        basis: tuple[np.ndarray, np.ndarray, np.ndarray],
        center_x: float,
        center_y: float,
        radius: float,
    ) -> GizmoProjection:
        right, up, view_dir = basis
        normal = direction / max(float(np.linalg.norm(direction)), 1e-12)
        x = float(np.dot(normal, right))
        y = float(np.dot(normal, up))
        depth = float(np.dot(normal, view_dir))
        return GizmoProjection(center_x + x * radius, center_y - y * radius, depth)

    def _draw_gizmo_circle(
        self,
        draw_list: Any,
        basis: tuple[np.ndarray, np.ndarray, np.ndarray],
        center_x: float,
        center_y: float,
        radius: float,
        direction_at: Any,
        front_color: int,
        back_color: int,
        thickness: float,
        closed: bool,
        t_min: float = 0.0,
        t_max: float = math.tau,
    ) -> None:
        samples = 96 if closed else 64
        points = [
            self._project_direction(direction_at(t), basis, center_x, center_y, radius)
            for t in np.linspace(t_min, t_max, samples)
        ]
        segment_count = len(points) if closed else len(points) - 1
        for index in range(segment_count):
            a = points[index]
            b = points[(index + 1) % len(points)]
            color = front_color if (a.depth + b.depth) * 0.5 >= 0.0 else back_color
            draw_list.add_line(a.x, a.y, b.x, b.y, color, thickness)


class GPUTerrainNpzViewerApp(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "GPU Terrain NPZ Viewer"
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
            radius=1.55,
            angles=(45.0, -45.0),
            aspect_ratio=self.wnd.aspect_ratio,
            near=0.01,
            far=100.0,
        )
        self.camera.projection.update(fov=45.0)
        self.camera.zoom_sensitivity = 0.05

        self.palette_names = ["Geology", "Topographic", "Ink"]
        self.palette = self._palette_override() if VIEWER_ARGS.palette else 0
        self.use_file_palette_on_load = VIEWER_ARGS.palette is None
        self.reset_camera_on_load = False
        self.model_matrix = np.eye(4, dtype="f4")
        self.model_matrix_bytes = self.model_matrix.tobytes()

        self.fps_timer = 0.0
        self.frame_count = 0
        self.last_time = time.perf_counter()
        self.target_fps = 60
        self.fps_val = 0.0
        self.export_files: list[Path] = []
        self.selected_export_index = 0
        self.load_status = ""
        self.export_path = Path(VIEWER_ARGS.path).resolve() if VIEWER_ARGS.path else newest_export()
        self.mesh: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}
        self.rows = 0
        self.cols = 0
        self.terrain_vbo: moderngl.Buffer | None = None
        self.ebo: moderngl.Buffer | None = None
        self.render_vao: moderngl.VertexArray | None = None

        self.refresh_export_files(self.export_path)
        self.load_export(self.export_path, apply_file_palette=True, reset_camera_view=False)
        self.ui = TerrainNpzInfoPanel(self.wnd)

    def _palette_override(self) -> int:
        return {"geology": 0, "topographic": 1, "ink": 2}[VIEWER_ARGS.palette]

    def _palette_from_metadata(self, metadata: dict[str, Any]) -> int:
        palette = str(metadata.get("palette", "Geology")).lower()
        if palette.startswith("topo"):
            return 1
        if palette.startswith("ink"):
            return 2
        return 0

    def is_sphere_terrain(self) -> bool:
        return self.metadata.get("generator_type") == "sphere_terrain"

    def light_pos(self) -> tuple[float, float, float]:
        if self.is_sphere_terrain():
            return SPHERE_LIGHT_POS
        return PLANE_LIGHT_POS

    def light_label(self) -> str:
        if self.is_sphere_terrain():
            return "Sphere generator"
        return "Plane generator"

    def refresh_export_files(self, selected_path: Path | None = None) -> None:
        selected = Path(selected_path or self.export_path).resolve()
        self.export_files = list_exported_npz_files(selected)
        self.selected_export_index = 0
        for index, path in enumerate(self.export_files):
            if path == selected:
                self.selected_export_index = index
                break
        self.load_status = f"Found {len(self.export_files)} export file(s)."

    def export_label(self, path: Path) -> str:
        try:
            relative = path.relative_to(PROJECT_ROOT)
            label = str(relative)
        except ValueError:
            label = str(path)
        return label.replace("\\", "/")

    def load_selected_export(self) -> None:
        if not self.export_files:
            self.load_status = "No export file is selected."
            return
        self.load_export(
            self.export_files[self.selected_export_index],
            apply_file_palette=self.use_file_palette_on_load,
            reset_camera_view=self.reset_camera_on_load,
        )

    def reload_current_export(self) -> None:
        self.load_export(
            self.export_path,
            apply_file_palette=self.use_file_palette_on_load,
            reset_camera_view=False,
        )

    def load_export_delta(self, delta: int) -> None:
        if not self.export_files:
            self.load_status = "No export file is selected."
            return
        self.selected_export_index = (self.selected_export_index + delta) % len(self.export_files)
        self.load_selected_export()

    def load_export(
        self,
        path: Path | str,
        *,
        apply_file_palette: bool,
        reset_camera_view: bool,
    ) -> None:
        terrain_path = Path(path).resolve()
        new_vbo: moderngl.Buffer | None = None
        new_ebo: moderngl.Buffer | None = None
        new_vao: moderngl.VertexArray | None = None
        try:
            mesh = load_exported_mesh(terrain_path)
            new_vbo = self.ctx.buffer(mesh["vertices"].tobytes())
            new_ebo = self.ctx.buffer(mesh["indices"].astype("u4").tobytes())
            new_vao = self.ctx.vertex_array(
                self.render_prog,
                [(new_vbo, "3f 3f 1f", "in_pos", "in_normal", "in_height")],
                index_buffer=new_ebo,
                index_element_size=4,
            )
        except Exception as exc:
            for resource in (new_vao, new_vbo, new_ebo):
                if resource is not None:
                    resource.release()
            self.load_status = f"Load failed: {exc}"
            print(self.load_status)
            if self.render_vao is None:
                raise
            return

        old_vao = self.render_vao
        old_vbo = self.terrain_vbo
        old_ebo = self.ebo

        self.export_path = terrain_path
        self.mesh = mesh
        self.metadata = mesh["metadata"]
        self.rows = int(mesh["rows"])
        self.cols = int(mesh["cols"])
        self.terrain_vbo = new_vbo
        self.ebo = new_ebo
        self.render_vao = new_vao

        for resource in (old_vao, old_vbo, old_ebo):
            if resource is not None:
                resource.release()

        if VIEWER_ARGS.palette:
            self.palette = self._palette_override()
        elif apply_file_palette:
            self.palette = self._palette_from_metadata(self.metadata)
        if reset_camera_view:
            self.reset_camera()

        self.refresh_export_files(terrain_path)
        self.load_status = f"Loaded {terrain_path.name}"
        self._print_loaded_summary()

    def _print_loaded_summary(self) -> None:
        print("=" * 72)
        print("GPU Terrain NPZ Viewer")
        print("-" * 72)
        print(f"File       : {self.export_path}")
        if self.metadata.get("generator_type") == "sphere_terrain":
            print(f"Mesh       : {self.metadata.get('topology', 'mesh')}")
        else:
            print(f"Grid       : {self.rows} x {self.cols}")
        print(f"Triangles  : {self.mesh['indices'].shape[0] // 3}")
        print(f"Height     : {self.mesh['height_min']:.6f} .. {self.mesh['height_max']:.6f}")
        print(f"Backend    : {self.metadata.get('backend', 'unknown')}")
        print(f"Layers     : {self.metadata.get('layer_count', 'unknown')}")
        print("-" * 72)
        print("Controls:")
        print("  Mouse drag  : Rotate camera")
        print("  Mouse wheel : Zoom")
        print("  C           : Cycle color palette")
        print("  HOME        : Reset camera")
        print("=" * 72)

    def reset_camera(self) -> None:
        self.camera.radius = 1.55
        self.camera.angle_x = 45.0
        self.camera.angle_y = -45.0

    def on_render(self, time_since_start: float, frametime: float):
        now = time.perf_counter()
        elapsed = now - self.last_time
        target_time = 1.0 / self.target_fps
        if elapsed < target_time:
            time.sleep(target_time - elapsed)
            now = time.perf_counter()
        self.last_time = now

        self.ctx.clear(0.055, 0.06, 0.065, 1.0)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)

        self.render_prog["m_proj"].write(self.camera.projection.matrix)
        self.render_prog["m_view"].write(self.camera.matrix)
        self.render_prog["m_model"].write(self.model_matrix_bytes)
        self.render_prog["u_palette"].value = int(self.palette)
        self.render_prog["u_light_pos"].value = self.light_pos()
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

        self.fps_timer += frametime
        self.frame_count += 1
        if self.fps_timer >= 0.5:
            self.fps_val = self.frame_count / self.fps_timer
            self.wnd.title = (
                f"GPU Terrain Viewer | {self.mesh_title_label()} | "
                f"{self.palette_names[self.palette]} | FPS: {self.fps_val:.1f}"
            )
            self.fps_timer = 0.0
            self.frame_count = 0

        self.ui.render(self)

    def mesh_title_label(self) -> str:
        if self.metadata.get("generator_type") == "sphere_terrain":
            return f"sphere {self.mesh['vertices'].shape[0]:,}v"
        return f"{self.rows}x{self.cols}"

    def on_key_event(self, key, action, modifiers):
        self.ui.key_event(key, action, modifiers)
        if action != self.wnd.keys.ACTION_PRESS:
            return

        if key == self.wnd.keys.C:
            self.palette = (self.palette + 1) % len(self.palette_names)
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
        self.camera.angle_y = max(min(self.camera.angle_y, -10.0), -170.0)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        self.ui.mouse_scroll_event(x_offset, y_offset)
        if self.ui.wants_mouse:
            return
        self.camera.radius = max(
            0.1,
            self.camera.radius - y_offset * self.camera.zoom_sensitivity,
        )

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


def main() -> None:
    mglw.run_window_config(
        GPUTerrainNpzViewerApp,
        args=MGLW_ARGS if MGLW_ARGS else ["--size_mult", "1"],
    )


if __name__ == "__main__":
    main()

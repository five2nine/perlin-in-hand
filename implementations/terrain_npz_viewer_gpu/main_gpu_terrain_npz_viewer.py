# GPU viewer for exported static terrain .npz meshes.

from __future__ import annotations

import argparse
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
GPU_TERRAIN_DIR = PROJECT_ROOT / "implementations" / "terrain_generation_gpu"
COMMON_DIR = PROJECT_ROOT / "implementations" / "terrain_generation_common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from terrain_npz_loader import load_exported_mesh, newest_export  # noqa: E402


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
        self.panel_height = 260.0

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
        self.panel_height = min(280.0, max(140.0, float(height) - margin * 2.0))

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
            imgui.text(f"FPS: {app.fps_val:.1f}")
            imgui.separator()
            imgui.text("Mouse drag rotate | Wheel zoom | C palette | HOME reset")
        imgui.end()


class GPUTerrainNpzViewerApp(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "GPU Terrain NPZ Viewer"
    window_size = (1920, 1080)
    aspect_ratio = None
    resizable = True
    vsync = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.export_path = Path(VIEWER_ARGS.path).resolve() if VIEWER_ARGS.path else newest_export()
        self.mesh = load_exported_mesh(self.export_path)
        self.metadata = self.mesh["metadata"]
        self.rows = int(self.mesh["rows"])
        self.cols = int(self.mesh["cols"])

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
        self.palette = self._initial_palette()
        self.model_matrix = np.eye(4, dtype="f4")
        self.model_matrix_bytes = self.model_matrix.tobytes()

        self.terrain_vbo = self.ctx.buffer(self.mesh["vertices"].tobytes())
        self.ebo = self.ctx.buffer(self.mesh["indices"].astype("u4").tobytes())
        self.render_vao = self.ctx.vertex_array(
            self.render_prog,
            [(self.terrain_vbo, "3f 3f 1f", "in_pos", "in_normal", "in_height")],
            index_buffer=self.ebo,
            index_element_size=4,
        )

        self.fps_timer = 0.0
        self.frame_count = 0
        self.last_time = time.perf_counter()
        self.target_fps = 60
        self.fps_val = 0.0
        self.ui = TerrainNpzInfoPanel(self.wnd)

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

    def _initial_palette(self) -> int:
        if VIEWER_ARGS.palette:
            return {"geology": 0, "topographic": 1, "ink": 2}[VIEWER_ARGS.palette]
        palette = str(self.metadata.get("palette", "Geology")).lower()
        if palette.startswith("topo"):
            return 1
        if palette.startswith("ink"):
            return 2
        return 0

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
        self.render_prog["u_light_pos"].value = (-0.35, 1.3, 0.45)
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
                f"GPU Terrain Viewer | {self.rows}x{self.cols} | "
                f"{self.palette_names[self.palette]} | FPS: {self.fps_val:.1f}"
            )
            self.fps_timer = 0.0
            self.frame_count = 0

        self.ui.render(self)

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

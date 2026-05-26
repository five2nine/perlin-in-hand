# Static CPU heightfield terrain generator with the same UI/output as the GPU version.

from __future__ import annotations

import os
import random
import sys
import time

import moderngl
import moderngl_window as mglw
import numpy as np
import pyglet
from moderngl_window.scene import OrbitCamera
from pyglet.gl import (
    GL_BLEND,
    GL_DEPTH_TEST,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_SRC_ALPHA,
    GL_TEXTURE0,
    GL_TEXTURE_2D,
    glActiveTexture,
    glBindTexture,
    glBindVertexArray,
    glBlendFunc,
    glDisable,
    glEnable,
    glUseProgram,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "terrain_generation_common"))
GPU_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "gpu_terrain_generation"))
if COMMON_DIR not in sys.path:
    sys.path.insert(0, COMMON_DIR)

from terrain_layers import (  # noqa: E402
    LayerKind,
    TerrainStack,
    compute_terrain_vertex_data,
)


with open(
    os.path.join(GPU_DIR, "shaders", "terrain_heightfield.vert"),
    "r",
    encoding="utf-8",
) as f:
    RENDER_VERTEX_SHADER = f.read()

with open(
    os.path.join(GPU_DIR, "shaders", "terrain_heightfield.frag"),
    "r",
    encoding="utf-8",
) as f:
    FRAGMENT_SHADER = f.read()


class CPUTerrainGeneratorApp(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "CPU Terrain Heightfield Generator"
    window_size = (1280, 720)
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

        self.resolution = 2**9
        self.palette = 0
        self.palette_names = ["Geology", "Topographic", "Ink"]
        self.rng = random.Random(6789)
        self.stack = TerrainStack.default()
        self.selected_layer = 0
        self.last_compute_ms = 0.0

        self.model_matrix = np.eye(4, dtype="f4")
        self.model_matrix_bytes = self.model_matrix.tobytes()

        self.ebo = None
        self.terrain_vbo = None
        self.render_vao = None
        self.rebuild_grid()
        self.upload_terrain_stack()

        self.fps_timer = 0.0
        self.frame_count = 0
        self.last_time = time.perf_counter()
        self.target_fps = 60
        self.fps_val = 0.0

        self.hud_label = pyglet.text.Label(
            "",
            font_name="Consolas",
            font_size=12,
            x=18,
            y=self.wnd.height - 18,
            width=680,
            multiline=True,
            color=(255, 255, 255, 225),
        )

        print("=" * 72)
        print("CPU Terrain Heightfield Generator (static f(x, y))")
        print("-" * 72)
        print("Controls:")
        print("  1 / 2 / 3      : Add random field layer with 1/2/3 octaves")
        print("  A              : Add random terrain layer")
        print("  V / B / G / W  : Add Valley / Billow / Ridged / Warped layer")
        print("  TAB            : Select next layer")
        print("  E              : Enable/disable selected layer")
        print("  BACKSPACE/DEL  : Remove selected layer")
        print("  [ / ]          : Lower/raise selected amplitude")
        print("  PAGE_UP/DOWN   : Raise/lower selected frequency")
        print("  R              : Reset terrain stack to default")
        print("  C              : Cycle color palette")
        print("  UP / DOWN      : Change grid resolution")
        print("  HOME           : Reset camera")
        print("  Mouse drag     : Rotate camera")
        print("=" * 72)

    def rebuild_grid(self) -> None:
        width = self.resolution
        height = self.resolution

        indices: list[int] = []
        for row in range(height - 1):
            for col in range(width - 1):
                bl = col + row * width
                br = col + 1 + row * width
                tl = col + (row + 1) * width
                tr = col + 1 + (row + 1) * width
                indices.extend([bl, br, tl, br, tr, tl])

        index_data = np.array(indices, dtype="u4")

        if self.ebo:
            self.ebo.release()
        if self.terrain_vbo:
            self.terrain_vbo.release()
        if self.render_vao:
            self.render_vao.release()

        self.ebo = self.ctx.buffer(index_data.tobytes())
        self.terrain_vbo = self.ctx.buffer(reserve=width * height * 7 * 4)
        self.render_vao = self.ctx.vertex_array(
            self.render_prog,
            [(self.terrain_vbo, "3f 3f 1f", "in_pos", "in_normal", "in_height")],
            index_buffer=self.ebo,
            index_element_size=4,
        )
        self.compute_terrain()

    def compute_terrain(self) -> None:
        if self.terrain_vbo is None:
            return
        start = time.perf_counter()
        vertex_data = compute_terrain_vertex_data(self.stack, self.resolution)
        self.terrain_vbo.write(vertex_data.tobytes())
        self.last_compute_ms = (time.perf_counter() - start) * 1000.0

    def upload_terrain_stack(self) -> None:
        self.render_prog["u_height_color_scale"].value = float(self.stack.height_color_scale())
        self.selected_layer = self.stack.clamp_index(self.selected_layer)
        self.compute_terrain()

    def add_random_layer(
        self,
        force_kind: LayerKind | None = None,
        octaves: int | None = None,
    ) -> None:
        self.selected_layer = self.stack.add_random_layer(
            self.rng,
            force_kind=force_kind,
            octaves=octaves,
        )
        self.upload_terrain_stack()

    def remove_selected_layer(self) -> None:
        self.selected_layer = self.stack.remove_layer(self.selected_layer)
        self.upload_terrain_stack()

    def selected(self):
        if not self.stack.layers:
            return None
        self.selected_layer = self.stack.clamp_index(self.selected_layer)
        return self.stack.layers[self.selected_layer]

    def reset_camera(self) -> None:
        self.camera.radius = 1.55
        self.camera.angle_x = 45.0
        self.camera.angle_y = -45.0

    def draw_hud(self) -> None:
        layer_lines: list[str] = []
        for idx, layer in enumerate(self.stack.layers[:8]):
            cursor = ">" if idx == self.selected_layer else " "
            layer_lines.append(f"{cursor}{idx:02d} {layer.summary()}")
        if len(self.stack.layers) > 8:
            layer_lines.append(f" ... {len(self.stack.layers) - 8} more")
        if not layer_lines:
            layer_lines.append(" no terrain layers")

        self.hud_label.text = (
            "[ CPU Terrain Heightfield ]\n"
            f"Grid      : {self.resolution} x {self.resolution}\n"
            f"Layers    : {len(self.stack.layers)} / 16\n"
            f"Compute   : {self.last_compute_ms:.2f} ms\n"
            f"Palette   : {self.palette_names[self.palette]}\n"
            f"FPS       : {self.fps_val:.1f}\n"
            "Controls  : A random, 1/2/3 octaves, V valley, W warp, DEL remove\n"
            + "\n".join(layer_lines)
        )

        glUseProgram(0)
        glBindVertexArray(0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.hud_label.draw()

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
                f"CPU Terrain | Grid: {self.resolution}x{self.resolution} | "
                f"Layers: {len(self.stack.layers)} | FPS: {self.fps_val:.1f}"
            )
            self.fps_timer = 0.0
            self.frame_count = 0

        self.draw_hud()

    def on_key_event(self, key, action, modifiers):
        if action != self.wnd.keys.ACTION_PRESS:
            return

        if key == self.wnd.keys.A:
            self.add_random_layer()
        elif key == self.wnd.keys.NUMBER_1:
            self.add_random_layer(force_kind=LayerKind.FBM, octaves=1)
        elif key == self.wnd.keys.NUMBER_2:
            self.add_random_layer(force_kind=LayerKind.FBM, octaves=2)
        elif key == self.wnd.keys.NUMBER_3:
            self.add_random_layer(force_kind=LayerKind.FBM, octaves=3)
        elif key == self.wnd.keys.V:
            self.add_random_layer(force_kind=LayerKind.VALLEY)
        elif key == self.wnd.keys.B:
            self.add_random_layer(force_kind=LayerKind.BILLOW)
        elif key == self.wnd.keys.G:
            self.add_random_layer(force_kind=LayerKind.RIDGED)
        elif key == self.wnd.keys.W:
            self.add_random_layer(force_kind=LayerKind.WARPED)
        elif key == self.wnd.keys.TAB:
            if self.stack.layers:
                self.selected_layer = (self.selected_layer + 1) % len(self.stack.layers)
        elif key in (self.wnd.keys.DELETE, self.wnd.keys.BACKSPACE):
            self.remove_selected_layer()
        elif key == self.wnd.keys.E:
            layer = self.selected()
            if layer is not None:
                layer.enabled = not layer.enabled
                self.upload_terrain_stack()
        elif key == self.wnd.keys.R:
            self.stack.reset_default()
            self.selected_layer = 0
            self.upload_terrain_stack()
        elif key == self.wnd.keys.C:
            self.palette = (self.palette + 1) % len(self.palette_names)
        elif key == self.wnd.keys.HOME:
            self.reset_camera()
        elif key == self.wnd.keys.UP:
            self.resolution = min(512, self.resolution + 20)
            self.rebuild_grid()
        elif key == self.wnd.keys.DOWN:
            self.resolution = max(32, self.resolution - 20)
            self.rebuild_grid()
        elif key == self.wnd.keys.PAGE_UP:
            layer = self.selected()
            if layer is not None:
                layer.frequency = min(64.0, layer.frequency + 0.75)
                self.upload_terrain_stack()
        elif key == self.wnd.keys.PAGE_DOWN:
            layer = self.selected()
            if layer is not None:
                layer.frequency = max(0.25, layer.frequency - 0.75)
                self.upload_terrain_stack()
        elif key == self.wnd.keys.LEFT_BRACKET:
            layer = self.selected()
            if layer is not None:
                layer.amplitude = max(0.0, layer.amplitude - 0.005)
                self.upload_terrain_stack()
        elif key == self.wnd.keys.RIGHT_BRACKET:
            layer = self.selected()
            if layer is not None:
                layer.amplitude = min(0.35, layer.amplitude + 0.005)
                self.upload_terrain_stack()

    def on_mouse_drag_event(self, x, y, dx, dy):
        if abs(dx) > 100 or abs(dy) > 100:
            return
        self.camera.angle_x += dx * self.camera.mouse_sensitivity / 10.0
        self.camera.angle_y += dy * self.camera.mouse_sensitivity / 10.0
        self.camera.angle_y = max(min(self.camera.angle_y, -10.0), -170.0)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        self.camera.radius = max(0.1, self.camera.radius - y_offset * self.camera.zoom_sensitivity)

    def on_resize(self, width: int, height: int):
        self.ctx.viewport = (0, 0, width, height)
        aspect = width / height if height > 0 else 1.0
        self.camera.projection.update(aspect_ratio=aspect)
        if hasattr(self, "hud_label") and self.hud_label:
            self.hud_label.y = height - 18


def main() -> None:
    mglw.run_window_config(CPUTerrainGeneratorApp)


if __name__ == "__main__":
    main()

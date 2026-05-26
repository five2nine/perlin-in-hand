# GPU Marching Squares for a 2D slice of a 3D simplex scalar field.

import os
import time

import moderngl
import moderngl_window as mglw
import pyglet
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
with open(
    os.path.join(SCRIPT_DIR, "shaders", "marching_squares.vert"),
    "r",
    encoding="utf-8",
) as f:
    VERTEX_SHADER = f.read()
with open(
    os.path.join(SCRIPT_DIR, "shaders", "marching_squares.frag"),
    "r",
    encoding="utf-8",
) as f:
    FRAGMENT_SHADER = f.read()
with open(
    os.path.join(SCRIPT_DIR, "shaders", "marching_squares_tf.vert"),
    "r",
    encoding="utf-8",
) as f:
    TF_VERTEX_SHADER = f.read()
with open(
    os.path.join(SCRIPT_DIR, "shaders", "marching_squares_tf.geom"),
    "r",
    encoding="utf-8",
) as f:
    TF_GEOMETRY_SHADER = f.read()


class SimplexMarchingSquaresApp(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "GPU Marching Squares Isolines"
    window_size = (1280, 720)
    resizable = True
    vsync = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER,
        )
        self.contour_prog = self.ctx.program(
            vertex_shader=TF_VERTEX_SHADER,
            geometry_shader=TF_GEOMETRY_SHADER,
            varyings=["out_pos", "out_value"],
        )

        self.resolution = 2**8
        self.frequency = 8.0
        self.threshold = 0.0
        self.field_mode = 0
        self.field_mode_names = ["Single", "fBm", "Ridged", "Billow"]
        self.octaves = 4
        self.persistence = 0.5
        self.lacunarity = 2.0
        self.palette = 0
        self.palette_names = ["Lagoon", "Neon", "Topographic", "Paper"]

        self.paused = False
        self.time_val = 0.0
        self.active_segment_count = 0

        self.contour_vao = self.ctx.vertex_array(self.contour_prog, [])
        self.contour_buffer = None
        self.line_vao = None
        self.rebuild_buffers()

        self.fps_timer = 0.0
        self.frame_count = 0
        self.last_time = time.perf_counter()
        self.target_fps = 60
        self.fps_val = 0.0

        self.hud_label = pyglet.text.Label(
            "",
            font_name="Consolas",
            font_size=12,
            x=20,
            y=self.wnd.height - 20,
            width=560,
            multiline=True,
            color=(255, 255, 255, 220),
        )

        print("=" * 60)
        print("GPU Marching Squares Isolines (ModernGL)")
        print("-" * 60)
        print("Controls:")
        print("  SPACE          : Pause/Resume field time coordinate")
        print("  C              : Cycle color palettes")
        print("  R              : Reset field parameters")
        print("  M              : Cycle field mode")
        print("  O              : Cycle octaves (1..8)")
        print("  P              : Adjust persistence (0.30..0.85)")
        print("  L              : Adjust lacunarity (1.5..3.0)")
        print("  UP / DOWN      : Change grid resolution (+/- 32)")
        print("  LEFT / RIGHT   : Adjust iso threshold (+/- 0.05)")
        print("  PAGE_UP / DOWN : Adjust frequency (+/- 1.0)")
        print("=" * 60)

    def buffer_size(self) -> int:
        max_vertices = (self.resolution - 1) ** 2 * 4
        floats_per_vertex = 3
        return max_vertices * floats_per_vertex * 4

    def rebuild_buffers(self):
        if self.contour_buffer:
            self.contour_buffer.release()
        if self.line_vao:
            self.line_vao.release()

        self.contour_buffer = self.ctx.buffer(reserve=self.buffer_size())
        self.line_vao = self.ctx.vertex_array(
            self.prog,
            [(self.contour_buffer, "2f 1f", "in_pos", "in_value")],
        )
        self.update_contours()

    def update_contours(self):
        self.contour_prog["u_time"].value = float(self.time_val)
        self.contour_prog["u_frequency"].value = float(self.frequency)
        self.contour_prog["u_grid_size"].value = int(self.resolution)
        self.contour_prog["u_threshold"].value = float(self.threshold)
        self.contour_prog["u_field_mode"].value = int(self.field_mode)
        self.contour_prog["u_octaves"].value = int(self.octaves)
        self.contour_prog["u_persistence"].value = float(self.persistence)
        self.contour_prog["u_lacunarity"].value = float(self.lacunarity)

        query = self.ctx.query(primitives=True)
        with query:
            self.contour_vao.transform(
                self.contour_buffer,
                vertices=(self.resolution - 1) ** 2,
            )
        self.active_segment_count = query.primitives

    def on_render(self, time_since_start: float, frametime: float):
        now = time.perf_counter()
        elapsed = now - self.last_time
        target_time = 1.0 / self.target_fps
        if elapsed < target_time:
            time.sleep(target_time - elapsed)
            now = time.perf_counter()
        self.last_time = now

        if not self.paused:
            self.time_val += frametime
            self.update_contours()

        self.ctx.clear(0.055, 0.065, 0.075, 1.0)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        viewport_width, viewport_height = self.ctx.viewport[2], self.ctx.viewport[3]
        self.prog["u_viewport_size"].value = (
            float(viewport_width),
            float(viewport_height),
        )
        self.prog["u_palette"].value = int(self.palette)
        self.prog["u_time"].value = float(self.time_val)

        if self.active_segment_count > 0:
            self.line_vao.render(
                moderngl.LINES,
                vertices=self.active_segment_count * 2,
            )

        self.fps_timer += frametime
        self.frame_count += 1
        if self.fps_timer >= 0.5:
            self.fps_val = self.frame_count / self.fps_timer
            self.wnd.title = (
                f"GPU Marching Squares | Grid: {self.resolution}x{self.resolution} | "
                f"Mode: {self.field_mode_names[self.field_mode]} | "
                f"Segments: {self.active_segment_count:,} | "
                f"Threshold: {self.threshold:.2f} | FPS: {self.fps_val:.1f}"
            )
            self.fps_timer = 0.0
            self.frame_count = 0

        self.hud_label.text = (
            "[ GPU Marching Squares ]\n"
            f"Grid Size : {self.resolution} x {self.resolution}\n"
            f"Segments  : {self.active_segment_count:,}\n"
            f"Mode      : {self.field_mode_names[self.field_mode]}\n"
            f"Octaves   : {self.octaves}\n"
            f"Frequency : {self.frequency:.1f}\n"
            f"Threshold : {self.threshold:.2f}\n"
            f"Persist.  : {self.persistence:.2f}\n"
            f"Lacunarity: {self.lacunarity:.1f}\n"
            f"Palette   : {self.palette_names[self.palette]}\n"
            f"FPS       : {self.fps_val:.1f}"
        )

        glUseProgram(0)
        glBindVertexArray(0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.hud_label.draw()

    def on_key_event(self, key, action, modifiers):
        if action != self.wnd.keys.ACTION_PRESS:
            return

        if key == self.wnd.keys.SPACE:
            self.paused = not self.paused
        elif key == self.wnd.keys.C:
            self.palette = (self.palette + 1) % len(self.palette_names)
        elif key == self.wnd.keys.R:
            self.frequency = 8.0
            self.threshold = 0.0
            self.field_mode = 0
            self.octaves = 4
            self.persistence = 0.5
            self.lacunarity = 2.0
            self.time_val = 0.0
            self.update_contours()
        elif key == self.wnd.keys.M:
            self.field_mode = (self.field_mode + 1) % len(self.field_mode_names)
            self.update_contours()
        elif key == self.wnd.keys.O:
            self.octaves = 1 if self.octaves >= 8 else self.octaves + 1
            self.update_contours()
        elif key == self.wnd.keys.P:
            self.persistence = 0.3 if self.persistence >= 0.85 else self.persistence + 0.05
            self.persistence = round(self.persistence, 2)
            self.update_contours()
        elif key == self.wnd.keys.L:
            self.lacunarity = 1.5 if self.lacunarity >= 3.0 else self.lacunarity + 0.1
            self.lacunarity = round(self.lacunarity, 1)
            self.update_contours()
        elif key == self.wnd.keys.UP:
            self.resolution = min(1024, self.resolution + 32)
            self.rebuild_buffers()
        elif key == self.wnd.keys.DOWN:
            self.resolution = max(32, self.resolution - 32)
            self.rebuild_buffers()
        elif key == self.wnd.keys.RIGHT:
            self.threshold = min(0.9, self.threshold + 0.05)
            self.update_contours()
        elif key == self.wnd.keys.LEFT:
            self.threshold = max(-0.9, self.threshold - 0.05)
            self.update_contours()
        elif key == self.wnd.keys.PAGE_UP:
            self.frequency = min(64.0, self.frequency + 1.0)
            self.update_contours()
        elif key == self.wnd.keys.PAGE_DOWN:
            self.frequency = max(1.0, self.frequency - 1.0)
            self.update_contours()

    def on_resize(self, width: int, height: int):
        self.ctx.viewport = (0, 0, width, height)
        if hasattr(self, "hud_label") and self.hud_label:
            self.hud_label.y = height - 20


def main() -> None:
    mglw.run_window_config(SimplexMarchingSquaresApp)


if __name__ == "__main__":
    main()

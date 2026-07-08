# 게임에서 지형을 만들 때 쓰는 특수한 수학 기법 #프로그래밍 #펄린노이즈 #수학 #절차적생성
# https://www.youtube.com/shorts/kY9TYQYxCZM

import os
import time
import numpy as np
import moderngl
import moderngl_window as mglw
import pyglet
from pyglet.gl import (
    glBindVertexArray,
    glUseProgram,
    glDisable,
    glEnable,
    glBlendFunc,
    GL_BLEND,
    GL_DEPTH_TEST,
    GL_SRC_ALPHA,
    GL_ONE_MINUS_SRC_ALPHA,
    glBindTexture,
    GL_TEXTURE_2D,
    glActiveTexture,
    GL_TEXTURE0
)
from moderngl_window.scene import OrbitCamera

# --- GLSL Shaders ---

# Load Vertex & Fragment Shaders from files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(SCRIPT_DIR, "shaders", "perlin_2002.vert"), "r", encoding="utf-8") as f:
    VERTEX_SHADER = f.read()
with open(os.path.join(SCRIPT_DIR, "shaders", "perlin_2002.frag"), "r", encoding="utf-8") as f:
    FRAGMENT_SHADER = f.read()


class PerlinNoise3DApp(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "Terrain Noise Workbench - Perlin Heightfield"
    window_size = (1280, 720)
    resizable = True
    vsync = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Create Shader Program
        self.prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER
        )

        # Setup Orbit Camera
        self.camera = OrbitCamera(
            target=(0.0, 0.0, 0.0),
            radius=1.5,
            angles=(45.0, -45.0),
            aspect_ratio=self.wnd.aspect_ratio,
            near=0.01,
            far=100.0
        )
        self.camera.projection.update(fov=45.0)
        self.camera.zoom_sensitivity = 0.05

        # Noise & Grid configuration
        self.resolution = 400
        self.frequency = 40.0
        self.amplitude = 0.05
        self.palette = 0
        self.palette_names = ["Viridis", "Magma", "Natural Terrain", "Cyberpunk Neon"]

        self.paused = False
        self.time_val = 0.0

        # Identity model matrix
        self.model_matrix = np.eye(4, dtype='f4')
        self.model_matrix_bytes = self.model_matrix.tobytes()

        # Buffers
        self.vbo = None
        self.ebo = None
        self.vao = None
        self.rebuild_grid()

        # FPS / UI Helper variables
        self.fps_timer = 0.0
        self.frame_count = 0
        self.last_time = time.perf_counter()
        self.target_fps = 60  # Cap FPS to 60 to avoid high GPU usage
        self.fps_val = 0.0

        # Setup 2D HUD text label using pyglet
        self.hud_label = pyglet.text.Label(
            "",
            font_name="Consolas",
            font_size=12,
            x=20,
            y=self.wnd.height - 20,
            width=500,
            multiline=True,
            color=(255, 255, 255, 220)
        )

        # Print controls to console
        print("=" * 60)
        print("Terrain Noise Workbench - Perlin Heightfield (ModernGL)")
        print("-" * 60)
        print("Controls:")
        print("  Mouse Drag (LMB) : Rotate Camera")
        print("  Mouse Scroll     : Zoom In/Out")
        print("  SPACE            : Pause/Resume Animation")
        print("  C                : Cycle Color Palettes")
        print("  W                : Toggle Wireframe Mode")
        print("  R                : Reset Camera Position")
        print("  UP / DOWN        : Change Grid Resolution (Resolution +/- 10)")
        print("  PAGE_UP / DOWN   : Adjust Wave Amplitude (Height +/- 0.01)")
        print("=" * 60)

    def rebuild_grid(self):
        """Generates grid vertex data (X,Y in [0,1]) and index buffer for rendering."""
        width = self.resolution
        height = self.resolution

        # 2D coordinates in XY plane
        x = np.linspace(0.0, 1.0, width, dtype='f4')
        y = np.linspace(0.0, 1.0, height, dtype='f4')
        X, Y = np.meshgrid(x, y)
        vertices = np.stack([X, Y], axis=-1).reshape(-1, 2)

        # Triangular index buffer
        indices = []
        for j in range(height - 1):
            for i in range(width - 1):
                bl = i + j * width
                br = (i + 1) + j * width
                tl = i + (j + 1) * width
                tr = (i + 1) + (j + 1) * width

                # Triangle 1
                indices.append(bl)
                indices.append(br)
                indices.append(tl)

                # Triangle 2
                indices.append(br)
                indices.append(tr)
                indices.append(tl)

        indices = np.array(indices, dtype='u4')

        # Cleanup old buffers
        if self.vbo:
            self.vbo.release()
        if self.ebo:
            self.ebo.release()
        if self.vao:
            self.vao.release()

        # Create new GPU buffers
        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.ebo = self.ctx.buffer(indices.tobytes())
        self.vao = self.ctx.vertex_array(
            self.prog,
            [(self.vbo, '2f', 'in_vert')],
            index_buffer=self.ebo,
            index_element_size=4
        )

    def on_render(self, time_since_start: float, frametime: float):
        # Cap FPS manually if VSync is disabled/overridden by graphics driver
        now = time.perf_counter()
        elapsed = now - self.last_time
        target_time = 1.0 / self.target_fps
        if elapsed < target_time:
            time.sleep(target_time - elapsed)
            now = time.perf_counter()
        self.last_time = now

        # Clear screen with slate-gray background
        self.ctx.clear(0.08, 0.08, 0.12, 1.0)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)

        # Update time parameter if not paused
        if not self.paused:
            self.time_val += frametime * 2.0

        # Bind and write uniforms
        self.prog['m_proj'].write(self.camera.projection.matrix)
        self.prog['m_view'].write(self.camera.matrix)
        self.prog['m_model'].write(self.model_matrix_bytes)
        
        self.prog['u_time'].value = float(self.time_val)
        self.prog['u_frequency'].value = float(self.frequency)
        self.prog['u_amplitude'].value = float(self.amplitude)
        self.prog['u_palette'].value = int(self.palette)

        # Dynamic light position: directly above the terrain center (Y=1.5)
        self.prog['u_light_pos'].value = (0.0, 1.5, 0.0)

        # Get view position safely
        try:
            view_pos = tuple(self.camera.position)
        except (TypeError, AttributeError):
            view_pos = (self.camera.position[0], self.camera.position[1], self.camera.position[2])
        self.prog['u_view_pos'].value = view_pos

        # Draw the terrain surface
        self.vao.render(moderngl.TRIANGLES)

        # Update FPS display in the title
        self.fps_timer += frametime
        self.frame_count += 1
        if self.fps_timer >= 0.5:
            self.fps_val = self.frame_count / self.fps_timer
            self.wnd.title = (
                f"3D Perlin Noise | Resolution: {self.resolution}x{self.resolution} | "
                f"Amp: {self.amplitude:.2f} | Palette: {self.palette_names[self.palette]} | "
                f"FPS: {self.fps_val:.1f}"
            )
            self.fps_timer = 0.0
            self.frame_count = 0

        # Update HUD label text
        self.hud_label.text = (
            f"[ 3D Perlin Noise ]\n"
            f"Resolution : {self.resolution} x {self.resolution}\n"
            f"Frequency  : {self.frequency:.1f}\n"
            f"Amplitude  : {self.amplitude:.2f}\n"
            f"Palette    : {self.palette_names[self.palette]}\n"
            f"FPS        : {self.fps_val:.1f}"
        )

        # Reset OpenGL state before drawing Pyglet label to avoid font corruption
        glUseProgram(0)
        glBindVertexArray(0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Render 2D HUD overlay
        self.hud_label.draw()

    def on_key_event(self, key, action, modifiers):
        if action == self.wnd.keys.ACTION_PRESS:
            # Toggle Wireframe mode
            if key == self.wnd.keys.W:
                self.ctx.wireframe = not self.ctx.wireframe
            # Pause / Resume
            elif key == self.wnd.keys.SPACE:
                self.paused = not self.paused
            # Cycle through color palettes
            elif key == self.wnd.keys.C:
                self.palette = (self.palette + 1) % len(self.palette_names)
            # Reset camera position
            elif key == self.wnd.keys.R:
                self.camera.radius = 1.5
                self.camera.angle_x = 45.0
                self.camera.angle_y = -45.0

            # Increase resolution
            elif key == self.wnd.keys.UP:
                self.resolution = min(400, self.resolution + 10)
                self.rebuild_grid()
            # Decrease resolution
            elif key == self.wnd.keys.DOWN:
                self.resolution = max(10, self.resolution - 10)
                self.rebuild_grid()
            # Increase wave amplitude
            elif key == self.wnd.keys.PAGE_UP:
                self.amplitude = min(0.5, self.amplitude + 0.01)
            # Decrease wave amplitude
            elif key == self.wnd.keys.PAGE_DOWN:
                self.amplitude = max(0.01, self.amplitude - 0.01)

    def on_mouse_drag_event(self, x, y, dx, dy):
        # Ignore mouse spikes that happen during window resize/maximize
        if abs(dx) > 100 or abs(dy) > 100:
            return
        # Custom rotation logic with safer clamping to avoid lookAt flipping at the poles
        self.camera.angle_x += dx * self.camera.mouse_sensitivity / 10.0
        self.camera.angle_y += dy * self.camera.mouse_sensitivity / 10.0
        self.camera.angle_y = max(min(self.camera.angle_y, -10.0), -170.0)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        self.camera.radius = max(0.1, self.camera.radius - y_offset * self.camera.zoom_sensitivity)

    def on_resize(self, width: int, height: int):
        self.ctx.viewport = (0, 0, width, height)
        aspect = width / height if height > 0 else 1.0
        self.camera.projection.update(aspect_ratio=aspect)
        if hasattr(self, 'hud_label') and self.hud_label:
            self.hud_label.y = height - 20


def main() -> None:
    mglw.run_window_config(PerlinNoise3DApp)

if __name__ == "__main__":
    main()

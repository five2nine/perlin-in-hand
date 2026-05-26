# 게임에서 지형을 만들 때 쓰는 특수한 수학 기법
# #프로그래밍 #오픈심플렉스노이즈 #수학 #절차적생성 #4차원노이즈 #볼륨렌더링 #복셀치즈

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
    GL_TEXTURE0,
)
from moderngl_window.scene import OrbitCamera
from marching_cubes_table import TRI_TABLE

# --- GLSL Shaders ---

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(
    os.path.join(SCRIPT_DIR, "shaders", "marching_cubes.vert"),
    "r",
    encoding="utf-8",
) as f:
    VERTEX_SHADER = f.read()
with open(
    os.path.join(SCRIPT_DIR, "shaders", "marching_cubes.frag"),
    "r",
    encoding="utf-8",
) as f:
    FRAGMENT_SHADER = f.read()
with open(
    os.path.join(SCRIPT_DIR, "shaders", "marching_cubes_tf.vert"),
    "r",
    encoding="utf-8",
) as f:
    TF_VERTEX_SHADER = f.read()
with open(
    os.path.join(SCRIPT_DIR, "shaders", "marching_cubes_tf.geom"),
    "r",
    encoding="utf-8",
) as f:
    TF_GEOMETRY_SHADER = f.read()


class OpenSimplexNoise4DApp(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "Real-Time Voxel Simplex Terrain"
    window_size = (1280, 720)
    resizable = True
    vsync = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Create Shader Program
        self.prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER, fragment_shader=FRAGMENT_SHADER
        )

        # Create Transform Feedback Shader Program for noise evaluation
        self.noise_prog = self.ctx.program(
            vertex_shader=TF_VERTEX_SHADER,
            geometry_shader=TF_GEOMETRY_SHADER,
            varyings=["out_pos", "out_normal", "out_height"],
        )

        # Setup Orbit Camera
        self.camera = OrbitCamera(
            target=(0.0, 0.0, 0.0),
            radius=1.8,  # Slightly pulled back for volume view
            angles=(45.0, -45.0),
            aspect_ratio=self.wnd.aspect_ratio,
            near=0.01,
            far=100.0,
        )
        self.camera.projection.update(fov=45.0)
        self.camera.zoom_sensitivity = 0.05

        # Voxel & Noise configuration
        self.resolution = 2 ** 6  # Voxel Grid size: resolution^3
        self.frequency = 6.0  # Lower frequency for larger, more visible cheese holes
        self.threshold = 0.05 * 6  # Anything below this threshold in noise is a hole
        self.slice_val = 0.0  # 4D W/time-axis slice coordinate
        self.palette = (
            2  # Default to Terrain (Natural colors fit cheese/soil block well)
        )
        self.palette_names = [
            "Viridis",
            "Magma",
            "Natural Cheese/Terrain",
            "Cyberpunk Neon",
        ]

        self.paused = True  # Time axis is fixed by default
        self.time_val = 0.0

        # Identity model matrix
        self.model_matrix = np.eye(4, dtype="f4")
        self.model_matrix_bytes = self.model_matrix.tobytes()

        # Performance optimization state
        self.active_voxel_count = 0

        # Compile triangulation table into a 2D integer texture
        tri_data = np.array(TRI_TABLE, dtype="i4").reshape(256, 16)
        self.tri_table_tex = self.ctx.texture(
            (16, 256), 1, data=tri_data.tobytes(), dtype="i4"
        )
        self.tri_table_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # Transform Feedback Setup (stores 7 floats: position(3), normal(3), height(1) = 28 bytes per vertex)
        self.noise_vao = self.ctx.vertex_array(self.noise_prog, [])
        # Cap the buffer size to 512MB to avoid 32-bit signed integer overflow (2GB limit)
        # and GPU out-of-memory errors.
        buffer_size = min((self.resolution - 1) ** 3 * 15 * 28, 512 * 1024 * 1024)
        self.noise_buffer = self.ctx.buffer(reserve=buffer_size)

        # Buffers (Static unit cube geometry)
        self.vbo = None
        self.ebo = None
        self.vao = None
        self.build_cube_buffers()

        # FBO Cache setup to achieve 0% GPU load when stationary
        self.fbo_color = None
        self.fbo_depth = None
        self.fbo = None
        self.create_fbo(self.wnd.buffer_size)

        # Screen quad for FBO rendering
        quad_vertices = np.array(
            [
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                1.0,
                1.0,
            ],
            dtype="f4",
        )
        self.quad_vbo = self.ctx.buffer(quad_vertices.tobytes())
        self.quad_program = self.ctx.program(
            vertex_shader="""
            #version 330
            in vec2 in_position;
            out vec2 v_texcoord;
            void main() {
                v_texcoord = in_position * 0.5 + 0.5;
                gl_Position = vec4(in_position, 0.0, 1.0);
            }
            """,
            fragment_shader="""
            #version 330
            uniform sampler2D u_texture;
            in vec2 v_texcoord;
            out vec4 f_color;
            void main() {
                f_color = texture(u_texture, v_texcoord);
            }
            """,
        )
        self.quad_vao = self.ctx.vertex_array(
            self.quad_program, [(self.quad_vbo, "2f", "in_position")]
        )
        self.dirty = True

        # Compute initial noise
        self.update_noise()

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
            color=(255, 255, 255, 220),
        )

        # Print controls to console
        print("=" * 60)
        print("Interactive Voxel Simplex Terrain Simulator (ModernGL)")
        print("-" * 60)
        print("Controls:")
        print("  Mouse Drag (LMB) : Rotate Camera")
        print("  Mouse Scroll     : Zoom In/Out")
        print("  SPACE            : Pause/Resume Animation (T-axis flow)")
        print("  C                : Cycle Color Palettes")
        print("  W                : Toggle Wireframe Mode")
        print("  R                : Reset Camera Position")
        print("  UP / DOWN        : Change Voxel Grid Size (Resolution +/- 8, Max 256)")
        print("  LEFT / RIGHT     : Adjust 4D W/Time Slice Coordinate (+/- 0.05)")
        print("  PAGE_UP / DOWN   : Adjust Density/Hole Threshold (+/- 0.05)")
        print("=" * 60)

    def create_fbo(self, size):
        """Creates or recreates the framebuffer cache matching the window resolution."""
        if hasattr(self, "fbo") and self.fbo:
            if self.fbo_color:
                self.fbo_color.release()
            if self.fbo_depth:
                self.fbo_depth.release()
            self.fbo.release()
        self.fbo_color = self.ctx.texture(size, 4)
        self.fbo_depth = self.ctx.depth_texture(size)
        self.fbo = self.ctx.framebuffer(self.fbo_color, self.fbo_depth)

    def build_cube_buffers(self):
        """Creates the vertex array linking the Transform Feedback buffer directly for rendering."""
        if self.vao:
            self.vao.release()

        # Link the TF buffer directly as standard vertex attributes (position, normal, height)
        self.vao = self.ctx.vertex_array(
            self.prog,
            [(self.noise_buffer, "3f 3f 1f", "in_pos", "in_normal", "in_height")]
        )

    def update_noise(self):
        """Runs the 4D noise transform feedback pass to bake the noise once on the GPU."""
        self.noise_prog["u_time"].value = float(self.time_val)
        self.noise_prog["u_frequency"].value = float(self.frequency)
        self.noise_prog["u_slice"].value = float(self.slice_val)
        self.noise_prog["u_grid_size"].value = int(self.resolution)
        self.noise_prog["u_threshold"].value = float(self.threshold)

        # Bind triangulation table texture
        self.tri_table_tex.use(location=0)
        self.noise_prog["u_tri_table"].value = 0

        # Execute TF and count how many active voxels were written using a Query
        query = self.ctx.query(primitives=True)
        with query:
            self.noise_vao.transform(self.noise_buffer, vertices=(self.resolution - 1) ** 3)
        self.active_voxel_count = query.primitives
        self.dirty = True

    def rebuild_voxel_grid(self):
        """Reallocates the GPU noise buffer and updates VAO linkages when resolution changes."""
        if hasattr(self, "noise_buffer") and self.noise_buffer:
            self.noise_buffer.release()
        # Cap the buffer size to 512MB to avoid 32-bit signed integer overflow (2GB limit)
        # and GPU out-of-memory errors.
        buffer_size = min((self.resolution - 1) ** 3 * 15 * 28, 512 * 1024 * 1024)
        self.noise_buffer = self.ctx.buffer(reserve=buffer_size)

        self.build_cube_buffers()
        self.update_noise()

    def on_render(self, time_since_start: float, frametime: float):
        # Cap FPS manually if VSync is disabled/overridden by graphics driver
        now = time.perf_counter()
        elapsed = now - self.last_time
        target_time = 1.0 / self.target_fps
        if elapsed < target_time:
            time.sleep(target_time - elapsed)
            now = time.perf_counter()
        self.last_time = now

        # Update time parameter if not paused
        if not self.paused:
            self.time_val += frametime * 0.4  # Slower, organic wave movement
            self.update_noise()
            self.dirty = True

        # Check if camera moved
        camera_matrix = self.camera.matrix
        if (
            not hasattr(self, "last_camera_matrix")
            or self.last_camera_matrix != camera_matrix
        ):
            self.dirty = True
            self.last_camera_matrix = type(camera_matrix)(camera_matrix)

        # Get view position safely
        try:
            view_pos = tuple(self.camera.position)
        except (TypeError, AttributeError):
            view_pos = (
                self.camera.position[0],
                self.camera.position[1],
                self.camera.position[2],
            )

        # If dirty, render 3D scene to FBO cache
        if self.dirty:
            self.fbo.use()
            self.fbo.clear(0.08, 0.08, 0.12, 1.0)
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.BLEND)

            # Bind and write uniforms
            self.prog["m_proj"].write(self.camera.projection.matrix)
            self.prog["m_view"].write(self.camera.matrix)
            self.prog["m_model"].write(self.model_matrix_bytes)

            self.prog["u_amplitude"].value = (
                0.5  # Constant for voxel height range [-0.5, 0.5]
            )
            self.prog["u_palette"].value = int(self.palette)

            # Dynamic light position: directly above the voxel grid center
            self.prog["u_light_pos"].value = (0.0, 2.0, 0.0)
            self.prog["u_view_pos"].value = view_pos

            # Draw the Marching Cubes triangles (active_voxel_count is query.primitives = triangles)
            if self.active_voxel_count > 0:
                self.vao.render(moderngl.TRIANGLES, vertices=self.active_voxel_count * 3)

            self.dirty = False

        # Render FBO texture to window backbuffer as a screen quad
        self.wnd.use()
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)

        self.fbo_color.use(location=0)
        self.quad_program["u_texture"].value = 0
        self.quad_vao.render(moderngl.TRIANGLE_STRIP)

        # Update FPS display in the title
        self.fps_timer += frametime
        self.frame_count += 1
        if self.fps_timer >= 0.5:
            self.fps_val = self.frame_count / self.fps_timer
            self.wnd.title = (
                f"GPU Marching Cubes Isosurface | Grid: {self.resolution}^3 | "
                f"Threshold: {self.threshold:.2f} | "
                f"W/Time Slice: {self.slice_val:.2f} | "
                f"FPS: {self.fps_val:.1f}"
            )
            self.fps_timer = 0.0
            self.frame_count = 0

        # Update HUD label text
        w_coord = self.slice_val + self.time_val
        self.hud_label.text = (
            f"[ GPU Marching Cubes Isosurface ]\n"
            f"Grid Size  : {self.resolution} x {self.resolution} x {self.resolution}\n"
            f"Triangles  : {self.active_voxel_count:,}\n"
            f"Vertices   : {self.active_voxel_count * 3:,}\n"
            f"Frequency  : {self.frequency:.1f} (Terrain Scale)\n"
            f"Threshold  : {self.threshold:.2f} (Density, PAGE_UP/DN)\n"
            f"4D W Slice : {self.slice_val:.2f} (LEFT/RIGHT)\n"
            f"Noise W    : slice + time = {w_coord:.2f}\n"
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
                self.dirty = True
            # Pause / Resume
            elif key == self.wnd.keys.SPACE:
                self.paused = not self.paused
                self.dirty = True
            # Cycle through color palettes
            elif key == self.wnd.keys.C:
                self.palette = (self.palette + 1) % len(self.palette_names)
                self.dirty = True
            # Reset camera position
            elif key == self.wnd.keys.R:
                self.camera.radius = 1.8
                self.camera.angle_x = 45.0
                self.camera.angle_y = -45.0
                self.dirty = True

            # Increase voxel grid size (max 256, supported since optimized with TF)
            elif key == self.wnd.keys.UP:
                self.resolution = min(256, self.resolution + 8)
                self.rebuild_voxel_grid()
            # Decrease voxel grid size
            elif key == self.wnd.keys.DOWN:
                self.resolution = max(8, self.resolution - 8)
                self.rebuild_voxel_grid()
            # Adjust density/hole threshold (PAGE_UP increases threshold, creating larger holes)
            elif key == self.wnd.keys.PAGE_UP:
                self.threshold = min(0.8, self.threshold + 0.05)
                self.update_noise()
            elif key == self.wnd.keys.PAGE_DOWN:
                self.threshold = max(-0.8, self.threshold - 0.05)
                self.update_noise()
            # Adjust the 4D W/time-axis slice coordinate and update noise buffer
            elif key == self.wnd.keys.RIGHT:
                self.slice_val += 0.05
                self.update_noise()
            elif key == self.wnd.keys.LEFT:
                self.slice_val -= 0.05
                self.update_noise()

    def on_mouse_drag_event(self, x, y, dx, dy):
        # Ignore mouse spikes that happen during window resize/maximize
        if abs(dx) > 100 or abs(dy) > 100:
            return
        # Custom rotation logic with safer clamping to avoid lookAt flipping at the poles
        self.camera.angle_x += dx * self.camera.mouse_sensitivity / 10.0
        self.camera.angle_y += dy * self.camera.mouse_sensitivity / 10.0
        self.camera.angle_y = max(min(self.camera.angle_y, -10.0), -170.0)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        self.camera.radius = max(
            0.1, self.camera.radius - y_offset * self.camera.zoom_sensitivity
        )

    def on_resize(self, width: int, height: int):
        self.ctx.viewport = (0, 0, width, height)
        aspect = width / height if height > 0 else 1.0
        self.camera.projection.update(aspect_ratio=aspect)
        if hasattr(self, "hud_label") and self.hud_label:
            self.hud_label.y = height - 20
        self.create_fbo((width, height))
        self.dirty = True


def main() -> None:
    mglw.run_window_config(OpenSimplexNoise4DApp)


if __name__ == "__main__":
    main()

import moderngl
import moderngl_window as mglw
import numpy as np

class TestTriangle(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "Test Triangle"
    window_size = (800, 600)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Simple shader that outputs red
        self.prog = self.ctx.program(
            vertex_shader="""
            #version 330
            in vec2 in_vert;
            void main() {
                gl_Position = vec4(in_vert, 0.0, 1.0);
            }
            """,
            fragment_shader="""
            #version 330
            out vec4 f_color;
            void main() {
                f_color = vec4(1.0, 0.0, 0.0, 1.0); // Bright Red
            }
            """
        )
        
        # Triangle vertices in NDC
        vertices = np.array([
            [-0.5, -0.5],
            [0.5, -0.5],
            [0.0, 0.5]
        ], dtype='f4')
        
        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.vao = self.ctx.vertex_array(self.prog, [(self.vbo, '2f', 'in_vert')])

    def on_render(self, time: float, frametime: float):
        self.ctx.clear(0.1, 0.2, 0.3, 1.0) # Dark Blue Background
        self.vao.render(moderngl.TRIANGLES)

if __name__ == '__main__':
    mglw.run_window_config(TestTriangle)

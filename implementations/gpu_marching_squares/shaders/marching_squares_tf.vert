#version 330

uniform int u_grid_size;

out vec2 v_cell_min;

void main() {
    int N = u_grid_size;
    int M = N - 1;
    int idx = gl_VertexID;

    int xi = idx % M;
    int yi = idx / M;

    v_cell_min = vec2(float(xi), float(yi)) / float(N - 1) - 0.5;
    gl_Position = vec4(v_cell_min, 0.0, 1.0);
}

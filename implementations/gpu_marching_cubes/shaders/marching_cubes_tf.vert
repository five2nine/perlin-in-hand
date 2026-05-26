#version 330

uniform int u_grid_size;

out vec3 v_cell_min; // Minimum corner of the cell in grid coords [-0.5, 0.5]

void main() {
    int N = u_grid_size;
    int M = N - 1; // Number of cells along each axis
    int idx = gl_VertexID;
    
    int xi = idx % M;
    int yi = (idx / M) % M;
    int zi = idx / (M * M);
    
    // Cell minimum corner scaled to range [-0.5, 0.5]
    v_cell_min = vec3(float(xi), float(yi), float(zi)) / float(N - 1) - 0.5;
    gl_Position = vec4(v_cell_min, 1.0);
}

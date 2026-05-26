#version 330

layout(points) in;
layout(points, max_vertices = 1) out;

in float v_noise[];
out vec4 out_voxel; // xyz: voxel_center, w: noise value

uniform float u_threshold;

void main() {
    if (v_noise[0] >= u_threshold) {
        out_voxel = vec4(gl_in[0].gl_Position.xyz, v_noise[0]);
        EmitVertex();
        EndPrimitive();
    }
}

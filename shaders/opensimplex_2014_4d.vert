#version 330

in vec3 in_pos;
in vec3 in_normal;
in vec4 in_voxel; // Instanced attribute: xyz = voxel_center, w = noise (divisor 1)

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;
uniform int u_grid_size; // default 40

out vec3 v_pos;
out vec3 v_normal;
out float v_height;

void main() {
    int N = u_grid_size;
    vec3 voxel_center = in_voxel.xyz;
    
    float scale = 0.90;
    
    // Offset and scale vertex position using pre-calculated voxel_center
    vec3 pos = voxel_center + in_pos * (scale / float(N));
    
    v_normal = normalize(mat3(m_model) * in_normal);
    vec4 world_pos = m_model * vec4(pos, 1.0);
    v_pos = world_pos.xyz;
    v_height = voxel_center.y; // Map height from [-0.5, 0.5]

    gl_Position = m_proj * m_view * world_pos;
}

#version 330

in vec3 in_pos;
in vec3 in_normal;
in float in_height;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;

out vec3 v_pos;
out vec3 v_normal;
out float v_height;

void main() {
    vec4 world_pos = m_model * vec4(in_pos, 1.0);
    v_pos = world_pos.xyz;
    v_normal = normalize(mat3(m_model) * in_normal);
    v_height = in_height;
    gl_Position = m_proj * m_view * world_pos;
}

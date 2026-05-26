#version 330

in vec2 in_pos;
in float in_value;

uniform vec2 u_viewport_size;

out float v_value;

void main() {
    vec2 viewport_size = max(u_viewport_size, vec2(1.0));
    vec2 scale = vec2(1.85);
    if (viewport_size.x > viewport_size.y) {
        scale.x *= viewport_size.y / viewport_size.x;
    } else {
        scale.y *= viewport_size.x / viewport_size.y;
    }

    v_value = in_value;
    gl_Position = vec4(in_pos * scale, 0.0, 1.0);
}

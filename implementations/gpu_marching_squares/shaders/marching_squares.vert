#version 330

in vec2 in_pos;
in float in_value;

uniform float u_aspect;

out float v_value;

void main() {
    vec2 p = in_pos * 1.85;
    if (u_aspect > 1.0) {
        p.x /= u_aspect;
    } else {
        p.y *= u_aspect;
    }

    v_value = in_value;
    gl_Position = vec4(p, 0.0, 1.0);
}

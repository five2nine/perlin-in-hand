#version 330

in float v_value;

uniform int u_palette;
uniform float u_time;

out vec4 f_color;

vec3 palette_color(int palette, float t) {
    if (palette == 0) {
        return mix(vec3(0.13, 0.70, 0.76), vec3(0.95, 0.91, 0.35), t);
    }
    if (palette == 1) {
        return mix(vec3(0.95, 0.22, 0.55), vec3(0.15, 0.78, 1.00), t);
    }
    if (palette == 2) {
        return mix(vec3(0.85, 0.92, 0.78), vec3(0.28, 0.58, 0.36), t);
    }
    return mix(vec3(0.88, 0.88, 0.92), vec3(1.00, 0.62, 0.18), t);
}

void main() {
    float t = 0.5 + 0.5 * sin(u_time * 0.7 + v_value * 8.0);
    vec3 color = palette_color(u_palette, t);
    f_color = vec4(color, 1.0);
}

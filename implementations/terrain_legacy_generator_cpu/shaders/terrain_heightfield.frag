#version 330

in vec3 v_pos;
in vec3 v_normal;
in float v_height;

uniform vec3 u_light_pos;
uniform vec3 u_view_pos;
uniform int u_palette;
uniform float u_height_color_scale;

out vec4 f_color;

vec3 col_geology(float t) {
    vec3 deep = vec3(0.08, 0.16, 0.23);
    vec3 moss = vec3(0.18, 0.38, 0.22);
    vec3 grass = vec3(0.43, 0.55, 0.24);
    vec3 rock = vec3(0.46, 0.42, 0.37);
    vec3 snow = vec3(0.92, 0.94, 0.92);
    if (t < 0.25) return mix(deep, moss, t / 0.25);
    if (t < 0.52) return mix(moss, grass, (t - 0.25) / 0.27);
    if (t < 0.78) return mix(grass, rock, (t - 0.52) / 0.26);
    return mix(rock, snow, (t - 0.78) / 0.22);
}

vec3 col_topo(float t) {
    vec3 low = vec3(0.11, 0.21, 0.33);
    vec3 mid = vec3(0.34, 0.62, 0.50);
    vec3 high = vec3(0.89, 0.74, 0.42);
    vec3 peak = vec3(0.96, 0.96, 0.90);
    if (t < 0.45) return mix(low, mid, t / 0.45);
    if (t < 0.78) return mix(mid, high, (t - 0.45) / 0.33);
    return mix(high, peak, (t - 0.78) / 0.22);
}

vec3 col_ink(float t) {
    vec3 a = vec3(0.09, 0.10, 0.12);
    vec3 b = vec3(0.55, 0.65, 0.68);
    vec3 c = vec3(0.95, 0.92, 0.78);
    if (t < 0.65) return mix(a, b, t / 0.65);
    return mix(b, c, (t - 0.65) / 0.35);
}

void main() {
    vec3 normal = normalize(v_normal);
    vec3 light_dir = normalize(u_light_pos - v_pos);
    vec3 view_dir = normalize(u_view_pos - v_pos);
    vec3 half_dir = normalize(light_dir + view_dir);

    float diffuse = max(dot(normal, light_dir), 0.0);
    float specular = pow(max(dot(normal, half_dir), 0.0), 48.0) * 0.28;
    float rim = pow(1.0 - max(dot(normal, view_dir), 0.0), 2.0) * 0.15;

    float scale = max(u_height_color_scale, 0.001);
    float h_norm = clamp(v_height / (scale * 2.0) + 0.5, 0.0, 1.0);

    vec3 base_color;
    if (u_palette == 1) {
        base_color = col_topo(h_norm);
    } else if (u_palette == 2) {
        base_color = col_ink(h_norm);
    } else {
        base_color = col_geology(h_norm);
    }

    vec3 color = base_color * (0.26 + diffuse * 0.78) + vec3(1.0) * specular + rim;
    f_color = vec4(color, 1.0);
}

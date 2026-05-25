#version 330

in vec3 v_pos;
in vec3 v_normal;
in float v_height;

uniform vec3 u_light_pos;
uniform vec3 u_view_pos;
uniform int u_palette;
uniform float u_amplitude;

out vec4 f_color;

// Palette 0: Viridis
vec3 col_viridis(float t) {
    vec3 c1 = vec3(0.267, 0.004, 0.329);
    vec3 c2 = vec3(0.191, 0.408, 0.553);
    vec3 c3 = vec3(0.128, 0.694, 0.490);
    vec3 c4 = vec3(0.992, 0.906, 0.144);
    if (t < 0.33) return mix(c1, c2, t / 0.33);
    if (t < 0.66) return mix(c2, c3, (t - 0.33) / 0.33);
    return mix(c3, c4, (t - 0.66) / 0.34);
}

// Palette 1: Magma
vec3 col_magma(float t) {
    vec3 c1 = vec3(0.05, 0.03, 0.10);
    vec3 c2 = vec3(0.45, 0.12, 0.38);
    vec3 c3 = vec3(0.89, 0.30, 0.20);
    vec3 c4 = vec3(0.98, 0.85, 0.36);
    if (t < 0.33) return mix(c1, c2, t / 0.33);
    if (t < 0.66) return mix(c2, c3, (t - 0.33) / 0.33);
    return mix(c3, c4, (t - 0.66) / 0.34);
}

// Palette 2: Natural Terrain
vec3 col_terrain(float t) {
    vec3 water_deep = vec3(0.01, 0.08, 0.3);
    vec3 water_shallow = vec3(0.0, 0.4, 0.6);
    vec3 sand = vec3(0.9, 0.8, 0.5);
    vec3 grass = vec3(0.15, 0.5, 0.15);
    vec3 rock = vec3(0.4, 0.35, 0.3);
    vec3 snow = vec3(0.95, 0.95, 0.95);
    if (t < 0.2) return mix(water_deep, water_shallow, t / 0.2);
    if (t < 0.25) return mix(water_shallow, sand, (t - 0.2) / 0.05);
    if (t < 0.6) return mix(sand, grass, (t - 0.25) / 0.35);
    if (t < 0.8) return mix(grass, rock, (t - 0.6) / 0.2);
    return mix(rock, snow, (t - 0.8) / 0.2);
}

// Palette 3: Cyberpunk / Neon
vec3 col_cyber(float t) {
    vec3 blue = vec3(0.0, 0.8, 1.0);
    vec3 purple = vec3(0.5, 0.0, 0.8);
    vec3 pink = vec3(1.0, 0.0, 0.5);
    if (t < 0.5) return mix(blue, purple, t / 0.5);
    return mix(purple, pink, (t - 0.5) / 0.5);
}

void main() {
    vec3 N = normalize(v_normal);
    vec3 L = normalize(u_light_pos - v_pos);
    vec3 V = normalize(u_view_pos - v_pos);
    vec3 H = normalize(L + V);

    float ambient = 0.22;
    float diffuse = max(dot(N, L), 0.0) * 0.70;
    float specular = pow(max(dot(N, H), 0.0), 32.0) * 0.45;

    // Normalize height based on current amplitude
    float h_norm = (v_height + u_amplitude) / (2.0 * u_amplitude);
    h_norm = clamp(h_norm, 0.0, 1.0);

    vec3 base_color;
    if (u_palette == 0) {
        base_color = col_viridis(h_norm);
    } else if (u_palette == 1) {
        base_color = col_magma(h_norm);
    } else if (u_palette == 2) {
        base_color = col_terrain(h_norm);
    } else {
        base_color = col_cyber(h_norm);
    }

    vec3 final_color = base_color * (ambient + diffuse) + vec3(1.0) * specular;
    f_color = vec4(final_color, 1.0);
}

#version 330

in vec2 in_vert;

uniform int u_grid_size;
uniform int u_layer_count;
uniform int u_layer_types[16];
uniform int u_layer_octaves[16];
uniform int u_layer_enabled[16];
uniform vec4 u_layer_params0[16]; // frequency, amplitude, persistence, lacunarity
uniform vec4 u_layer_params1[16]; // seed_x, seed_y, rotation, valley_power
uniform vec4 u_layer_params2[16]; // warp_strength, warp_frequency, warp_seed_x, warp_seed_y

out vec3 out_pos;
out vec3 out_normal;
out float out_height;

const int MAX_LAYERS = 16;
const int MAX_OCTAVES = 3;
const float PI2 = 6.28318530718;

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec2 gradient(vec2 p, float seed) {
    float angle = hash12(p + vec2(seed, seed * 0.37)) * PI2;
    return vec2(cos(angle), sin(angle));
}

vec2 fade2(vec2 t) {
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

float gradient_noise(vec2 p, float seed) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = fade2(f);

    float n00 = dot(gradient(i + vec2(0.0, 0.0), seed), f - vec2(0.0, 0.0));
    float n10 = dot(gradient(i + vec2(1.0, 0.0), seed), f - vec2(1.0, 0.0));
    float n01 = dot(gradient(i + vec2(0.0, 1.0), seed), f - vec2(0.0, 1.0));
    float n11 = dot(gradient(i + vec2(1.0, 1.0), seed), f - vec2(1.0, 1.0));

    float nx0 = mix(n00, n10, u.x);
    float nx1 = mix(n01, n11, u.x);
    return clamp(mix(nx0, nx1, u.y) * 1.41421356237, -1.0, 1.0);
}

vec2 rotate_uv(vec2 uv, float angle) {
    float c = cos(angle);
    float s = sin(angle);
    vec2 centered = uv - vec2(0.5);
    return vec2(
        c * centered.x - s * centered.y,
        s * centered.x + c * centered.y
    ) + vec2(0.5);
}

float sample_base(int index, vec2 uv, float frequency, float seed_shift) {
    vec4 p1 = u_layer_params1[index];
    float seed = p1.x * 0.13 + p1.y * 0.17 + seed_shift;
    return gradient_noise(uv * frequency + p1.xy, seed);
}

float sample_fbm(int index, vec2 uv) {
    vec4 p0 = u_layer_params0[index];
    float total = 0.0;
    float amplitude = 1.0;
    float frequency = p0.x;
    float amplitude_sum = 0.0;

    for (int octave = 0; octave < MAX_OCTAVES; octave++) {
        if (octave >= u_layer_octaves[index]) break;
        total += sample_base(index, uv, frequency, float(octave) * 19.19) * amplitude;
        amplitude_sum += amplitude;
        frequency *= p0.w;
        amplitude *= p0.z;
    }

    if (amplitude_sum <= 0.0) return 0.0;
    return total / amplitude_sum;
}

vec2 transform_layer_uv(int index, vec2 uv) {
    vec4 p1 = u_layer_params1[index];
    vec4 p2 = u_layer_params2[index];
    vec2 result = rotate_uv(uv, p1.z);

    if (p2.x > 0.0) {
        float wx = gradient_noise(result * p2.y + p2.zw, p2.z * 0.07 + 11.0);
        float wy = gradient_noise(result * p2.y + p2.zw + vec2(37.2, -19.1), p2.w * 0.07 + 29.0);
        result += vec2(wx, wy) * p2.x;
    }

    return result;
}

float sample_layer(int index, vec2 uv) {
    int kind = u_layer_types[index];
    vec4 p0 = u_layer_params0[index];
    vec4 p1 = u_layer_params1[index];
    vec2 tuv = transform_layer_uv(index, uv);

    float value = 0.0;
    if (kind == 0) {
        if (u_layer_octaves[index] <= 1) {
            value = sample_base(index, tuv, p0.x, 0.0);
        } else {
            value = sample_fbm(index, tuv);
        }
    } else if (kind == 1 || kind == 5) {
        value = sample_fbm(index, tuv);
    } else if (kind == 2) {
        value = (1.0 - abs(sample_fbm(index, tuv))) * 2.0 - 1.0;
    } else if (kind == 3) {
        value = abs(sample_fbm(index, tuv)) * 2.0 - 1.0;
    } else if (kind == 4) {
        float valley = max(0.0, 1.0 - abs(sample_fbm(index, tuv)));
        value = -pow(valley, p1.w);
    }

    return value * p0.y;
}

float get_height(vec2 uv) {
    float height = 0.0;

    for (int index = 0; index < MAX_LAYERS; index++) {
        if (index >= u_layer_count) break;
        if (u_layer_enabled[index] == 0) continue;
        height += sample_layer(index, uv);
    }

    return height;
}

void main() {
    float eps = 1.0 / max(float(u_grid_size - 1), 1.0);
    float h0 = get_height(in_vert);
    float hx = get_height(in_vert + vec2(eps, 0.0));
    float hy = get_height(in_vert + vec2(0.0, eps));

    out_pos = vec3(in_vert.x - 0.5, h0, in_vert.y - 0.5);

    vec3 tx = vec3(eps, hx - h0, 0.0);
    vec3 tz = vec3(0.0, hy - h0, eps);
    out_normal = normalize(cross(tz, tx));
    out_height = h0;
}

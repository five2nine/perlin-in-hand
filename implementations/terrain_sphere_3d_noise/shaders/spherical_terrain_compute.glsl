#version 430

layout(local_size_x = 128) in;

layout(std430, binding = 0) readonly buffer DirectionBuffer {
    vec4 directions[];
};

layout(std430, binding = 1) writeonly buffer TerrainBuffer {
    float terrain[];
};

uniform int u_vertex_count;
uniform int u_octaves;
uniform float u_frequency;
uniform float u_amplitude;
uniform float u_persistence;
uniform float u_lacunarity;
uniform float u_seed;

const float TAU = 6.28318530718;

float fade(float value) {
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0);
}

vec3 fade3(vec3 value) {
    return vec3(fade(value.x), fade(value.y), fade(value.z));
}

float hash3(vec3 cell, float salt) {
    float value = sin(dot(cell, vec3(127.1, 311.7, 74.7)) + salt * 269.5);
    return fract(value * 43758.5453123);
}

vec3 gradient(vec3 cell, float seed) {
    float h0 = hash3(cell, seed);
    float h1 = hash3(cell, seed + 17.0);
    float gz = h0 * 2.0 - 1.0;
    float radius = sqrt(max(1.0 - gz * gz, 0.0));
    float angle = h1 * TAU;
    return vec3(cos(angle) * radius, sin(angle) * radius, gz);
}

float gradient_dot(vec3 cell, vec3 point, float seed) {
    return dot(gradient(cell, seed), point - cell);
}

float gradient_noise_3d(vec3 point, float seed) {
    vec3 p0 = floor(point);
    vec3 p1 = p0 + vec3(1.0);
    vec3 s = fade3(point - p0);

    float n000 = gradient_dot(vec3(p0.x, p0.y, p0.z), point, seed);
    float n100 = gradient_dot(vec3(p1.x, p0.y, p0.z), point, seed);
    float n010 = gradient_dot(vec3(p0.x, p1.y, p0.z), point, seed);
    float n110 = gradient_dot(vec3(p1.x, p1.y, p0.z), point, seed);
    float n001 = gradient_dot(vec3(p0.x, p0.y, p1.z), point, seed);
    float n101 = gradient_dot(vec3(p1.x, p0.y, p1.z), point, seed);
    float n011 = gradient_dot(vec3(p0.x, p1.y, p1.z), point, seed);
    float n111 = gradient_dot(vec3(p1.x, p1.y, p1.z), point, seed);

    float nx00 = mix(n000, n100, s.x);
    float nx10 = mix(n010, n110, s.x);
    float nx01 = mix(n001, n101, s.x);
    float nx11 = mix(n011, n111, s.x);
    float nxy0 = mix(nx00, nx10, s.y);
    float nxy1 = mix(nx01, nx11, s.y);
    return clamp(mix(nxy0, nxy1, s.z) * 1.73205080757, -1.0, 1.0);
}

float sample_fbm(vec3 direction) {
    float total = 0.0;
    float amplitude = 1.0;
    float frequency = u_frequency;
    float amplitude_sum = 0.0;
    int octave_count = clamp(u_octaves, 1, 8);
    vec3 seed_offset = vec3(u_seed * 0.11, u_seed * -0.07, u_seed * 0.19);

    for (int octave = 0; octave < 8; ++octave) {
        if (octave >= octave_count) {
            break;
        }
        vec3 point = direction * frequency + seed_offset;
        total += gradient_noise_3d(point, u_seed + float(octave) * 23.31) * amplitude;
        amplitude_sum += amplitude;
        frequency *= u_lacunarity;
        amplitude *= u_persistence;
    }

    return total / max(amplitude_sum, 0.00000001) * u_amplitude;
}

vec3 displaced_position(vec3 direction) {
    float height = sample_fbm(direction);
    return direction * (1.0 + height);
}

vec3 sample_normal(vec3 direction) {
    float finest_frequency = u_frequency * pow(u_lacunarity, float(max(u_octaves - 1, 0)));
    float step_size = clamp(0.35 / max(finest_frequency, 1.0), 0.001, 0.015);
    vec3 reference = abs(direction.y) < 0.96 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
    vec3 tangent = normalize(cross(reference, direction));
    vec3 bitangent = normalize(cross(direction, tangent));

    vec3 tangent_plus = displaced_position(normalize(direction + tangent * step_size));
    vec3 tangent_minus = displaced_position(normalize(direction - tangent * step_size));
    vec3 bitangent_plus = displaced_position(normalize(direction + bitangent * step_size));
    vec3 bitangent_minus = displaced_position(normalize(direction - bitangent * step_size));
    vec3 normal = normalize(cross(tangent_plus - tangent_minus, bitangent_plus - bitangent_minus));
    if (dot(normal, direction) < 0.0) {
        normal *= -1.0;
    }
    return normal;
}

void write_vertex(uint index, vec3 position, vec3 normal, float height) {
    uint base = index * 7u;
    terrain[base + 0u] = position.x;
    terrain[base + 1u] = position.y;
    terrain[base + 2u] = position.z;
    terrain[base + 3u] = normal.x;
    terrain[base + 4u] = normal.y;
    terrain[base + 5u] = normal.z;
    terrain[base + 6u] = height;
}

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= uint(u_vertex_count)) {
        return;
    }

    vec3 direction = normalize(directions[index].xyz);
    float height = sample_fbm(direction);
    vec3 position = direction * (1.0 + height);
    vec3 normal = sample_normal(direction);
    write_vertex(index, position, normal, height);
}

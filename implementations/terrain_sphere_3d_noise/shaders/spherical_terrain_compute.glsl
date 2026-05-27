#version 430

layout(local_size_x = 128) in;

layout(std430, binding = 0) writeonly buffer TerrainBuffer {
    float terrain[];
};

uniform int u_draw_vertex_count;
uniform int u_subdivision_steps;
uniform int u_octaves;
uniform float u_frequency;
uniform float u_amplitude;
uniform float u_persistence;
uniform float u_lacunarity;
uniform float u_seed;

const float TAU = 6.28318530718;
const float PHI = 1.61803398875;

vec3 base_vertex(int index) {
    vec3 vertex = vec3(0.0);
    if (index == 0) vertex = vec3(-1.0, PHI, 0.0);
    else if (index == 1) vertex = vec3(1.0, PHI, 0.0);
    else if (index == 2) vertex = vec3(-1.0, -PHI, 0.0);
    else if (index == 3) vertex = vec3(1.0, -PHI, 0.0);
    else if (index == 4) vertex = vec3(0.0, -1.0, PHI);
    else if (index == 5) vertex = vec3(0.0, 1.0, PHI);
    else if (index == 6) vertex = vec3(0.0, -1.0, -PHI);
    else if (index == 7) vertex = vec3(0.0, 1.0, -PHI);
    else if (index == 8) vertex = vec3(PHI, 0.0, -1.0);
    else if (index == 9) vertex = vec3(PHI, 0.0, 1.0);
    else if (index == 10) vertex = vec3(-PHI, 0.0, -1.0);
    else vertex = vec3(-PHI, 0.0, 1.0);
    return normalize(vertex);
}

ivec3 base_face(int index) {
    if (index == 0) return ivec3(0, 11, 5);
    if (index == 1) return ivec3(0, 5, 1);
    if (index == 2) return ivec3(0, 1, 7);
    if (index == 3) return ivec3(0, 7, 10);
    if (index == 4) return ivec3(0, 10, 11);
    if (index == 5) return ivec3(1, 5, 9);
    if (index == 6) return ivec3(5, 11, 4);
    if (index == 7) return ivec3(11, 10, 2);
    if (index == 8) return ivec3(10, 7, 6);
    if (index == 9) return ivec3(7, 1, 8);
    if (index == 10) return ivec3(3, 9, 4);
    if (index == 11) return ivec3(3, 4, 2);
    if (index == 12) return ivec3(3, 2, 6);
    if (index == 13) return ivec3(3, 6, 8);
    if (index == 14) return ivec3(3, 8, 9);
    if (index == 15) return ivec3(4, 9, 5);
    if (index == 16) return ivec3(2, 4, 11);
    if (index == 17) return ivec3(6, 2, 10);
    if (index == 18) return ivec3(8, 6, 7);
    return ivec3(9, 8, 1);
}

vec3 subdivided_direction(vec3 a, vec3 b, vec3 c, int i, int j, int steps) {
    float u = float(i) / float(steps);
    float v = float(j) / float(steps);
    float w = 1.0 - u - v;
    return normalize(a * w + b * u + c * v);
}

vec3 direction_for_draw_vertex(uint draw_vertex_index) {
    int steps = max(u_subdivision_steps, 1);
    uint triangle_index = draw_vertex_index / 3u;
    int corner = int(draw_vertex_index - triangle_index * 3u);
    uint triangles_per_base_face = uint(steps * steps);
    int base_face_index = int(triangle_index / triangles_per_base_face);
    int local_triangle = int(triangle_index - uint(base_face_index) * triangles_per_base_face);

    int row = int(floor(float(steps) - sqrt(float(steps * steps - local_triangle))));
    row = clamp(row, 0, steps - 1);
    while (local_triangle < row * (2 * steps - row)) {
        row -= 1;
    }
    while (local_triangle >= (row + 1) * (2 * steps - row - 1)) {
        row += 1;
    }

    int row_start = row * (2 * steps - row);
    int remaining = local_triangle - row_start;
    bool upward = (remaining % 2) == 0;
    int col = remaining / 2;
    int i = col;
    int j = row;

    ivec3 face = base_face(base_face_index);
    vec3 a = base_vertex(face.x);
    vec3 b = base_vertex(face.y);
    vec3 c = base_vertex(face.z);

    if (upward) {
        if (corner == 0) return subdivided_direction(a, b, c, i, j, steps);
        if (corner == 1) return subdivided_direction(a, b, c, i + 1, j, steps);
        return subdivided_direction(a, b, c, i, j + 1, steps);
    }

    if (corner == 0) return subdivided_direction(a, b, c, i + 1, j, steps);
    if (corner == 1) return subdivided_direction(a, b, c, i + 1, j + 1, steps);
    return subdivided_direction(a, b, c, i, j + 1, steps);
}

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
    if (index >= uint(u_draw_vertex_count)) {
        return;
    }

    vec3 direction = direction_for_draw_vertex(index);
    float height = sample_fbm(direction);
    vec3 position = direction * (1.0 + height);
    vec3 normal = sample_normal(direction);
    write_vertex(index, position, normal, height);
}

#version 330

layout(points) in;
layout(triangle_strip, max_vertices = 15) out;

in vec3 v_cell_min[1];

uniform float u_time;
uniform float u_frequency;
uniform float u_slice;
uniform int u_grid_size;
uniform float u_threshold;
uniform isampler2D u_tri_table;

out vec3 out_pos;
out vec3 out_normal;
out float out_height;

// --- Ashima Arts / Stefan Gustavson's 4D Simplex Noise ---
vec4 mod289(vec4 x) {
    return x - floor(x * (1.0 / 289.0)) * 289.0;
}

float mod289(float x) {
    return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 permute(vec4 x) {
    return mod289(((x * 34.0) + 10.0) * x);
}

float permute(float x) {
    return mod289(((x * 34.0) + 10.0) * x);
}

vec4 taylorInvSqrt(vec4 r) {
    return 1.79284291400159 - 0.85373472095314 * r;
}

float taylorInvSqrt(float r) {
    return 1.79284291400159 - 0.85373472095314 * r;
}

vec4 grad4(float j, vec4 ip) {
    const vec4 ones = vec4(1.0, 1.0, 1.0, -1.0);
    vec4 p, s;
    p.xyz = floor(fract(vec3(j) * ip.xyz) * 7.0) * ip.z - 1.0;
    p.w = 1.5 - dot(abs(p.xyz), ones.xyz);
    s = vec4(lessThan(p, vec4(0.0)));
    p.xyz = p.xyz + (s.xyz * 2.0 - 1.0) * s.www;
    return p;
}

#define F4 0.309016994374947451

float snoise(vec4 v) {
    const vec4 C = vec4(0.138196601125011,  // (5 - sqrt(5))/20  G4
                        0.276393202250021,  // 2 * G4
                        0.414589803375032,  // 3 * G4
                       -0.447213595499958); // -1 + 4 * G4

    // First corner
    vec4 i = floor(v + dot(v, vec4(F4)));
    vec4 x0 = v - i + dot(i, C.xxxx);

    // Other corners
    vec4 i0;
    vec3 isX = step(x0.yzw, x0.xxx);
    vec3 isYZ = step(x0.zww, x0.yyz);
    i0.x = isX.x + isX.y + isX.z;
    i0.yzw = 1.0 - isX;
    i0.y += isYZ.x + isYZ.y;
    i0.zw += 1.0 - isYZ.xy;
    i0.z += isYZ.z;
    i0.w += 1.0 - isYZ.z;

    vec4 i3 = clamp(i0, 0.0, 1.0);
    vec4 i2 = clamp(i0 - 1.0, 0.0, 1.0);
    vec4 i1 = clamp(i0 - 2.0, 0.0, 1.0);

    vec4 x1 = x0 - i1 + C.xxxx;
    vec4 x2 = x0 - i2 + C.yyyy;
    vec4 x3 = x0 - i3 + C.zzzz;
    vec4 x4 = x0 + C.wwww;

    // Permutations
    i = mod289(i);
    float j0 = permute(permute(permute(permute(i.w) + i.z) + i.y) + i.x);
    vec4 j1 = permute(permute(permute(permute(i.w + vec4(i1.w, i2.w, i3.w, 1.0))
            + i.z + vec4(i1.z, i2.z, i3.z, 1.0))
            + i.y + vec4(i1.y, i2.y, i3.y, 1.0))
            + i.x + vec4(i1.x, i2.x, i3.x, 1.0));

    // Gradients
    vec4 ip = vec4(1.0 / 294.0, 1.0 / 49.0, 1.0 / 7.0, 0.0);
    vec4 p0 = grad4(j0, ip);
    vec4 p1 = grad4(j1.x, ip);
    vec4 p2 = grad4(j1.y, ip);
    vec4 p3 = grad4(j1.z, ip);
    vec4 p4 = grad4(j1.w, ip);

    // Normalization
    vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;
    p4 *= taylorInvSqrt(dot(p4, p4));

    // Mix contributions
    vec3 m0 = max(0.6 - vec3(dot(x0, x0), dot(x1, x1), dot(x2, x2)), 0.0);
    vec2 m1 = max(0.6 - vec2(dot(x3, x3), dot(x4, x4)), 0.0);
    m0 = m0 * m0;
    m1 = m1 * m1;
    return 49.0 * (dot(m0 * m0, vec3(dot(p0, x0), dot(p1, x1), dot(p2, x2))) 
                 + dot(m1 * m1, vec2(dot(p3, x3), dot(p4, x4))));
}

float get_density(vec3 grid_pos, float freq, float slice_time) {
    return snoise(vec4(grid_pos * freq, slice_time));
}

// Linear interpolation between two corner positions based on their densities
vec3 interp(vec3 pA, vec3 pB, float dA, float dB) {
    if (abs(u_threshold - dA) < 0.00001) return pA;
    if (abs(u_threshold - dB) < 0.00001) return pB;
    if (abs(dA - dB) < 0.00001) return pA;
    float mu = (u_threshold - dA) / (dB - dA);
    return pA + mu * (pB - pA);
}

// Map edge index to interpolated vertex position
vec3 get_edge_vertex(int edge, vec3 p0, vec3 p1, vec3 p2, vec3 p3, vec3 p4, vec3 p5, vec3 p6, vec3 p7,
                     float d0, float d1, float d2, float d3, float d4, float d5, float d6, float d7) {
    if (edge == 0) return interp(p0, p1, d0, d1);
    if (edge == 1) return interp(p1, p2, d1, d2);
    if (edge == 2) return interp(p2, p3, d2, d3);
    if (edge == 3) return interp(p3, p0, d3, d0);
    if (edge == 4) return interp(p4, p5, d4, d5);
    if (edge == 5) return interp(p5, p6, d5, d6);
    if (edge == 6) return interp(p6, p7, d6, d7);
    if (edge == 7) return interp(p7, p4, d7, d4);
    if (edge == 8) return interp(p0, p4, d0, d4);
    if (edge == 9) return interp(p1, p5, d1, d5);
    if (edge == 10) return interp(p2, p6, d2, d6);
    if (edge == 11) return interp(p3, p7, d3, d7);
    return vec3(0.0);
}

// Compute normal using finite difference gradient of the noise density field
vec3 get_normal(vec3 pos) {
    float eps = 0.005;
    float dx = get_density(pos + vec3(eps, 0.0, 0.0), u_frequency, u_slice + u_time) - get_density(pos - vec3(eps, 0.0, 0.0), u_frequency, u_slice + u_time);
    float dy = get_density(pos + vec3(0.0, eps, 0.0), u_frequency, u_slice + u_time) - get_density(pos - vec3(0.0, eps, 0.0), u_frequency, u_slice + u_time);
    float dz = get_density(pos + vec3(0.0, 0.0, eps), u_frequency, u_slice + u_time) - get_density(pos - vec3(0.0, 0.0, eps), u_frequency, u_slice + u_time);
    vec3 grad = vec3(dx, dy, dz);
    float len = length(grad);
    if (len < 0.0001) return vec3(0.0, 1.0, 0.0);
    return -normalize(grad);
}

void main() {
    float step_val = 1.0 / float(u_grid_size - 1);
    
    // 8 corner positions of the cell
    vec3 p0 = v_cell_min[0] + vec3(0.0, 0.0, 0.0);
    vec3 p1 = v_cell_min[0] + vec3(step_val, 0.0, 0.0);
    vec3 p2 = v_cell_min[0] + vec3(step_val, step_val, 0.0);
    vec3 p3 = v_cell_min[0] + vec3(0.0, step_val, 0.0);
    vec3 p4 = v_cell_min[0] + vec3(0.0, 0.0, step_val);
    vec3 p5 = v_cell_min[0] + vec3(step_val, 0.0, step_val);
    vec3 p6 = v_cell_min[0] + vec3(step_val, step_val, step_val);
    vec3 p7 = v_cell_min[0] + vec3(0.0, step_val, step_val);
    
    // Sample densities
    float d0 = get_density(p0, u_frequency, u_slice + u_time);
    float d1 = get_density(p1, u_frequency, u_slice + u_time);
    float d2 = get_density(p2, u_frequency, u_slice + u_time);
    float d3 = get_density(p3, u_frequency, u_slice + u_time);
    float d4 = get_density(p4, u_frequency, u_slice + u_time);
    float d5 = get_density(p5, u_frequency, u_slice + u_time);
    float d6 = get_density(p6, u_frequency, u_slice + u_time);
    float d7 = get_density(p7, u_frequency, u_slice + u_time);
    
    // Compute 8-bit cube index
    int cubeindex = 0;
    if (d0 >= u_threshold) cubeindex |= 1;
    if (d1 >= u_threshold) cubeindex |= 2;
    if (d2 >= u_threshold) cubeindex |= 4;
    if (d3 >= u_threshold) cubeindex |= 8;
    if (d4 >= u_threshold) cubeindex |= 16;
    if (d5 >= u_threshold) cubeindex |= 32;
    if (d6 >= u_threshold) cubeindex |= 64;
    if (d7 >= u_threshold) cubeindex |= 128;
    
    // Cell is entirely inside or outside the surface
    if (cubeindex == 0 || cubeindex == 255) return;
    
    // Process triangulation (up to 5 triangles)
    for (int i = 0; i < 16; i += 3) {
        int e0 = texelFetch(u_tri_table, ivec2(i, cubeindex), 0).r;
        if (e0 == -1) break;
        int e1 = texelFetch(u_tri_table, ivec2(i + 1, cubeindex), 0).r;
        int e2 = texelFetch(u_tri_table, ivec2(i + 2, cubeindex), 0).r;
        
        vec3 v0 = get_edge_vertex(e0, p0, p1, p2, p3, p4, p5, p6, p7, d0, d1, d2, d3, d4, d5, d6, d7);
        vec3 v1 = get_edge_vertex(e1, p0, p1, p2, p3, p4, p5, p6, p7, d0, d1, d2, d3, d4, d5, d6, d7);
        vec3 v2 = get_edge_vertex(e2, p0, p1, p2, p3, p4, p5, p6, p7, d0, d1, d2, d3, d4, d5, d6, d7);
        
        // Output triangle vertex 0
        out_pos = v0;
        out_normal = get_normal(v0);
        out_height = v0.y;
        EmitVertex();
        
        // Output triangle vertex 1
        out_pos = v1;
        out_normal = get_normal(v1);
        out_height = v1.y;
        EmitVertex();
        
        // Output triangle vertex 2
        out_pos = v2;
        out_normal = get_normal(v2);
        out_height = v2.y;
        EmitVertex();
        
        EndPrimitive();
    }
}

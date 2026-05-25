#version 330

uniform float u_time;
uniform float u_frequency;
uniform float u_slice;
uniform int u_grid_size;
uniform float u_threshold;

out float v_noise;

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

void main() {
    int N = u_grid_size;
    int idx = gl_VertexID;
    
    // Decode gl_VertexID to 3D grid coordinate (xi, yi, zi)
    int xi = idx % N;
    int yi = (idx / N) % N;
    int zi = idx / (N * N);
    
    // Center the voxel grid around (0,0,0) in range [-0.5, 0.5]
    vec3 voxel_center = vec3(float(xi), float(yi), float(zi)) / float(N - 1) - 0.5;
    
    float center_density = get_density(voxel_center, u_frequency, u_slice + u_time);
    
    // If the current voxel is solid
    if (center_density >= u_threshold) {
        // Step size between neighboring grid points
        float step_val = 1.0 / float(N - 1);
        
        bool on_surface = false;
        
        // Check 6 neighbors: Left, Right, Down, Up, Back, Front.
        // If we are on the grid boundary, we treat the outside as empty (air) -> visible face.
        if (xi == 0 || get_density(voxel_center + vec3(-step_val, 0.0, 0.0), u_frequency, u_slice + u_time) < u_threshold) {
            on_surface = true;
        } else if (xi == N - 1 || get_density(voxel_center + vec3(step_val, 0.0, 0.0), u_frequency, u_slice + u_time) < u_threshold) {
            on_surface = true;
        } else if (yi == 0 || get_density(voxel_center + vec3(0.0, -step_val, 0.0), u_frequency, u_slice + u_time) < u_threshold) {
            on_surface = true;
        } else if (yi == N - 1 || get_density(voxel_center + vec3(0.0, step_val, 0.0), u_frequency, u_slice + u_time) < u_threshold) {
            on_surface = true;
        } else if (zi == 0 || get_density(voxel_center + vec3(0.0, 0.0, -step_val), u_frequency, u_slice + u_time) < u_threshold) {
            on_surface = true;
        } else if (zi == N - 1 || get_density(voxel_center + vec3(0.0, 0.0, step_val), u_frequency, u_slice + u_time) < u_threshold) {
            on_surface = true;
        }
        
        if (on_surface) {
            v_noise = center_density;
            gl_Position = vec4(voxel_center, 1.0);
        } else {
            // Discard: Voxel is solid but completely hidden inside the terrain
            v_noise = -999.0;
            gl_Position = vec4(0.0);
        }
    } else {
        // Discard: Voxel is empty air
        v_noise = -999.0;
        gl_Position = vec4(0.0);
    }
}

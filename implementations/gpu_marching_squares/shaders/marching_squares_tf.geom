#version 330

layout(points) in;
layout(line_strip, max_vertices = 4) out;

in vec2 v_cell_min[1];

uniform float u_time;
uniform float u_frequency;
uniform int u_grid_size;
uniform float u_threshold;

out vec2 out_pos;
out float out_value;

// Ashima Arts / Stefan Gustavson 3D simplex noise.
// snoise is the conventional short name for simplex noise.
vec3 mod289(vec3 x) {
    return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 mod289(vec4 x) {
    return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 permute(vec4 x) {
    return mod289(((x * 34.0) + 10.0) * x);
}

vec4 taylorInvSqrt(vec4 r) {
    return 1.79284291400159 - 0.85373472095314 * r;
}

float snoise(vec3 v) {
    const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

    vec3 i = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);

    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);

    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;

    i = mod289(i);
    vec4 p = permute(
        permute(
            permute(i.z + vec4(0.0, i1.z, i2.z, 1.0))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0)
        )
        + i.x + vec4(0.0, i1.x, i2.x, 1.0)
    );

    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;

    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);

    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);

    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);

    vec4 s0 = floor(b0) * 2.0 + 1.0;
    vec4 s1 = floor(b1) * 2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));

    vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);

    vec4 norm = taylorInvSqrt(
        vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3))
    );
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;

    vec4 m = max(
        0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)),
        0.0
    );
    m = m * m;
    return 42.0 * dot(
        m * m,
        vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3))
    );
}

float get_density(vec2 grid_pos) {
    return snoise(vec3(grid_pos * u_frequency, u_time));
}

vec2 interp(vec2 pA, vec2 pB, float dA, float dB) {
    if (abs(u_threshold - dA) < 0.00001) return pA;
    if (abs(u_threshold - dB) < 0.00001) return pB;
    if (abs(dA - dB) < 0.00001) return pA;
    float mu = (u_threshold - dA) / (dB - dA);
    return pA + mu * (pB - pA);
}

void emit_segment(vec2 a, vec2 b) {
    out_value = u_threshold;
    out_pos = a;
    EmitVertex();

    out_value = u_threshold;
    out_pos = b;
    EmitVertex();

    EndPrimitive();
}

void main() {
    float step_val = 1.0 / float(u_grid_size - 1);

    vec2 p0 = v_cell_min[0] + vec2(0.0, 0.0);
    vec2 p1 = v_cell_min[0] + vec2(step_val, 0.0);
    vec2 p2 = v_cell_min[0] + vec2(step_val, step_val);
    vec2 p3 = v_cell_min[0] + vec2(0.0, step_val);

    float d0 = get_density(p0);
    float d1 = get_density(p1);
    float d2 = get_density(p2);
    float d3 = get_density(p3);

    int square_index = 0;
    if (d0 >= u_threshold) square_index |= 1;
    if (d1 >= u_threshold) square_index |= 2;
    if (d2 >= u_threshold) square_index |= 4;
    if (d3 >= u_threshold) square_index |= 8;

    if (square_index == 0 || square_index == 15) return;

    vec2 e0 = interp(p0, p1, d0, d1);
    vec2 e1 = interp(p1, p2, d1, d2);
    vec2 e2 = interp(p2, p3, d2, d3);
    vec2 e3 = interp(p3, p0, d3, d0);

    if (square_index == 1) {
        emit_segment(e3, e0);
    } else if (square_index == 2) {
        emit_segment(e0, e1);
    } else if (square_index == 3) {
        emit_segment(e3, e1);
    } else if (square_index == 4) {
        emit_segment(e1, e2);
    } else if (square_index == 5) {
        emit_segment(e3, e0);
        emit_segment(e1, e2);
    } else if (square_index == 6) {
        emit_segment(e0, e2);
    } else if (square_index == 7) {
        emit_segment(e3, e2);
    } else if (square_index == 8) {
        emit_segment(e2, e3);
    } else if (square_index == 9) {
        emit_segment(e0, e2);
    } else if (square_index == 10) {
        emit_segment(e0, e1);
        emit_segment(e2, e3);
    } else if (square_index == 11) {
        emit_segment(e1, e2);
    } else if (square_index == 12) {
        emit_segment(e1, e3);
    } else if (square_index == 13) {
        emit_segment(e0, e1);
    } else if (square_index == 14) {
        emit_segment(e3, e0);
    }
}

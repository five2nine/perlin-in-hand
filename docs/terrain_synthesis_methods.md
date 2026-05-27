# 🏔️ 실시간 3D 지형 합성 및 가공 기법 (Terrain Synthesis Methods)

본 문서는 단순 노이즈(Single-octave Noise)가 가지는 평면적이고 인공적인 형태의 한계를 극복하고, 실제 대자연과 같이 사실적인 산맥, 계곡, 평야를 조각하기 위해 사용되는 **다양한 지형 합성 및 수학적 가공 기법**을 정리한 가이드입니다. 

CPU(Python)와 GPU(GLSL Vertex Shader) 환경 모두에서 즉시 적용할 수 있도록 핵심 개념과 함께 코드 스니펫을 제공합니다.

---

## 1. 지형 합성 및 가공 핵심 기법 요약

| 기법명 | 수학적 원리 / 공식 | 시각적 특징 및 효과 | 주요 용도 |
| :--- | :--- | :--- | :--- |
| **1. 옥타브 합성 (fBm)** | 여러 주파수와 진폭의 노이즈 누적 합산 | 큰 굴곡 위에 세밀한 돌출부가 얹힌 기하학적 형태 | 사실적인 대형 산맥, 지표면 거칠기 표현 |
| **2. 리짓 노이즈 (Ridged)** | $1.0 - \lvert Noise(x, y) \rvert$ (절댓값 반전) | 정상이 칼날처럼 뾰족하고 매끄러운 빗살 모양 능선 | 알프스산맥 등 깎아지른 산줄기, 융기 지형 |
| **3. 빌로우 노이즈 (Billow)** | $\lvert Noise(x, y) \rvert$ (단순 절댓값) | 둥글둥글하게 솟구친 구름이나 뽈록한 모래 언덕 형태 | 사막의 모래 언덕(Dune), 뭉게구름 지형 |
| **4. 거듭제곱 (Exponentiation)** | $(Noise \times 0.5 + 0.5)^p \quad (p \ge 2)$ | 봉우리는 뾰족하게 유지하고 골짜기/평야는 평평하게 폄 | 산맥 사이의 넓은 평원(Valley) 및 해분 분리 |
| **5. 도메인 워핑 (Warping)** | $Noise(x + Noise(x, y), y + Noise(x, y))$ | 격자가 유기적으로 뒤틀려 구불구불하게 흐르는 형태 | 강줄기, 침식된 퇴적암 협곡(Canyon) |
| **6. 바이옴 마스킹 (Masking)** | $Flat \times (1 - Mask) + Mountain \times Mask$ | 산맥 지대와 넓은 평야가 권역별로 뭉쳐서 나타남 | 대규모 바이옴(Biome) 분리 및 대자연 스케일감 구현 |

---

## 2. 기법별 세부 개념 및 GLSL 구현 예시

### 2.1. 옥타브 합성 (fBm - Fractal Brownian Motion)
자연의 모든 지형은 멀리서 볼 때의 거대한 윤곽과 가까이서 볼 때의 자잘한 요철이 공존하는 **자기 유사성(Fractal)**을 띱니다. 
주파수(Frequency)를 2배씩 늘리고 진폭(Amplitude)을 절반씩 줄여가며 여러 번 노이즈를 더해 이 특성을 모방합니다.

* **지속도(Persistence, $p$)**: 다음 옥타브로 넘어갈 때 진폭이 줄어드는 비율 (대개 $0.5$)
* **라쿠나리티(Lacunarity, $l$)**: 다음 옥타브로 넘어갈 때 주파수가 늘어나는 비율 (대개 $2.0$)

#### GLSL 버텍스 셰이더 예시:
```glsl
float get_fbm_height(vec2 uv) {
    float height = 0.0;
    float freq = u_frequency;
    float amp = u_amplitude;
    float max_value = 0.0; // 정규화를 위한 누적 최댓값
    
    // 4개의 옥타브 합성
    for(int i = 0; i < 4; i++) {
        height += cnoise(vec3(uv * freq, u_time * 0.5)) * amp;
        max_value += amp;
        freq *= 2.0; // 라쿠나리티 적용 (주파수 2배)
        amp *= 0.5;  // 지속도 적용 (진폭 절반)
    }
    
    return height;
}
```

---

### 2.2. 리짓 노이즈 (Ridged Multi-fractal)
단순 펄린 노이즈는 산꼭대기가 항상 둥근 둔덕 모양이 되는 한계가 있습니다. 
노이즈 결과에 절댓값을 취하면 계곡처럼 깊게 파인 $V$자 골짜기가 형성되는데, 이를 뒤집어서 정상이 날카로운 칼날 형태의 산맥으로 만듭니다.

#### GLSL 버텍스 셰이더 예시:
```glsl
float get_ridged_height(vec2 uv) {
    // 1. 기본 노이즈 추출 (결과: -1.0 ~ 1.0)
    float n = cnoise(vec3(uv * u_frequency, u_time));
    
    // 2. 절댓값을 취하고 반전시켜 뾰족한 능선 생성 (결과: 0.0 ~ 1.0)
    float ridge = 1.0 - abs(n);
    
    // 3. 능선을 더 날카롭게 가공하기 위해 제곱 적용
    ridge = ridge * ridge;
    
    return ridge * u_amplitude;
}
```

---

### 2.3. 비선형 매핑 및 거듭제곱 (Exponentiation)
지형의 고도 데이터를 비선형적으로 왜곡하여 높은 산봉우리는 급격한 경사를 갖게 하고, 고도가 낮은 분지나 계곡은 넓고 평평한 평야로 만들어 사실감을 극대화합니다.

#### GLSL 버텍스 셰이더 예시:
```glsl
float get_plain_mountain_height(vec2 uv) {
    // 1. 노이즈 범위를 0.0 ~ 1.0 으로 변환
    float n = cnoise(vec3(uv * u_frequency, u_time)) * 0.5 + 0.5;
    
    // 2. 거듭제곱 적용 (p = 3.0)
    // 낮은 값(예: 0.2)은 0.008로 극도로 평평해지고, 높은 값(예: 0.9)은 0.729로 높게 유지됨
    float shaped = pow(n, 3.0);
    
    return shaped * u_amplitude;
}
```

---

### 2.4. 도메인 워핑 (Domain Warping)
그리드 기반 노이즈의 고유한 직사각형 또는 규칙적인 정렬 배열을 무너뜨려 자연스러운 침식 지형과 굽이치는 절벽을 표현합니다. 
노이즈를 계산할 때 입력 좌표(`uv`) 자체를 다른 노이즈의 연산 결과로 밀어내어 왜곡시킵니다.

#### GLSL 버텍스 셰이더 예시:
```glsl
float get_warped_height(vec2 uv) {
    // 1. 좌표를 왜곡할 오프셋 벡터를 다른 노이즈로 연산
    vec2 offset;
    offset.x = cnoise(vec3(uv * u_frequency + vec2(1.2, 3.4), u_time * 0.2));
    offset.y = cnoise(vec3(uv * u_frequency + vec2(5.6, 7.8), u_time * 0.2));
    
    // 2. 왜곡 강도 조절 후 원본 좌표에 더함
    vec2 warped_uv = uv + offset * 0.05;
    
    // 3. 왜곡된 좌표로 최종 노이즈 연산
    return cnoise(vec3(warped_uv * u_frequency, u_time)) * u_amplitude;
}
```

---

### 2.5. 바이옴 마스킹 (Biome Masking)
대규모 세계관을 지닌 지형에서는 산맥지대와 평야지대가 자연스럽게 뭉쳐있어야 합니다. 
초저주파(매우 넓은 영역)의 마스크 노이즈를 사용하여 두 지형을 블렌딩합니다.

#### GLSL 버텍스 셰이더 예시:
```glsl
float get_biome_terrain(vec2 uv) {
    // 1. 초대형 스케일(낮은 주파수)의 마스크 연산
    float mask = cnoise(vec3(uv * (u_frequency * 0.1), u_time * 0.05)) * 0.5 + 0.5;
    mask = smoothstep(0.3, 0.7, mask); // 경계면을 부드럽게 보간
    
    // 2. 평야형 지형 (낮고 부드러움)
    float flat_terrain = pow(cnoise(vec3(uv * u_frequency, u_time)) * 0.5 + 0.5, 3.0) * 0.02;
    
    // 3. 산악형 지형 (높고 날카로움)
    float mountain_terrain = (1.0 - abs(cnoise(vec3(uv * u_frequency, u_time)))) * u_amplitude;
    
    // 4. 두 바이옴을 마스크 값을 기준으로 결합
    return mix(flat_terrain, mountain_terrain, mask);
}
```

---

## 3. 종합 실전 적용 예시: 하이브리드 멀티프랙탈 지형
이 기법들을 모두 융합하여 **도메인 워핑이 적용된 옥타브 합성 산줄기 + 비선형 거듭제곱으로 다듬어진 평야**를 셰이더 1개 내부에서 조합해 내는 최종 버텍스 셰이더 예시입니다.

```glsl
// 지형 생성 핵심 함수 (fBm + Exponentiation + Warping)
float get_final_terrain_height(vec2 uv) {
    // 1. 도메인 워핑 적용
    vec2 warp_offset;
    warp_offset.x = cnoise(vec3(uv * 10.0, u_time * 0.1)) * 0.02;
    warp_offset.y = cnoise(vec3(uv * 10.0 + vec2(1.7), u_time * 0.1)) * 0.02;
    vec2 final_uv = uv + warp_offset;

    // 2. 옥타브 합성(fBm)
    float height = 0.0;
    float freq = u_frequency;
    float amp = u_amplitude;
    float max_amp = 0.0;

    for (int i = 0; i < 4; i++) {
        // 리짓 노이즈 기법 융합 (1.0 - |noise|)
        float n = cnoise(vec3(final_uv * freq, u_time * (1.0 + float(i)*0.15)));
        float r = 1.0 - abs(n);
        
        height += r * amp;
        max_amp += amp;
        
        freq *= 2.1;
        amp *= 0.45;
    }
    
    // 3. 정규화
    height /= max_amp;

    // 4. 거듭제곱 변환 (높은 곳은 날카롭게 살리고 낮은 평지는 완전히 죽임)
    height = pow(height, 2.5) * u_amplitude * 2.0;

    return height;
}
```
이 셰이더를 현재 프로젝트의 `implementations/heightfield_gpu/shaders/perlin_2002.vert` 또는 `implementations/heightfield_gpu/shaders/opensimplex_2014.vert` 내부의 `get_height` 함수 자리에 대체하면, 기존의 단순했던 빨래판 지형이 즉각적으로 **웅장한 실시간 3D 산맥 지형**으로 뒤바뀝니다.

# 구면 Terrain을 이해하기 위한 노트

## 핵심 질문

평면 terrain은 보통 다음처럼 생각한다.

```text
height = f(x, y)
position = (x, height, y)
```

구면 terrain은 다음처럼 생각한다.

```text
direction = normalize(position_on_sphere)
height = f(direction)
position = direction * (radius + height)
```

두 식은 비슷해 보이지만 의미가 다르다. 평면 terrain은 고정된 위쪽 방향으로 높이를 올린다. 구면 terrain은 각 지점마다 바깥쪽 방향이 다르므로 높이를 방사 방향으로 올린다. 이 차이 때문에 같은 노이즈라도 평면에 그렸을 때와 구면에 그렸을 때 인상이 다르게 보인다.

## 평면 Heightfield

평면 heightfield의 도메인은 사각형이다.

```text
(x, y) in [0, 1] x [0, 1]
```

샘플 격자는 정사각형으로 깔리고, 각 점은 같은 방향의 높이축을 가진다.

```text
up = (0, 1, 0)
surface_position = (x - 0.5, height, y - 0.5)
```

평면에서는 전역적인 `x`, `y`, `up`이 모두 명확하다. 카메라로 볼 때도 지형의 높낮이가 같은 방향으로 쌓인다. 그래서 산, 계곡, ridged noise 같은 패턴을 읽기 쉽다.

## 구면 Terrain

구면에는 하나의 전역 `up`이 없다. 모든 점의 `up`은 구의 중심에서 표면으로 나가는 방향이다.

```text
direction = normalize(vertex)
up_at_point = direction
surface_position = direction * (radius + height)
```

이 방식은 지형이 구의 표면을 따라 감싸진다. 같은 높이 변화라도 적도, 극점, 옆면에서 보는 방향이 다르므로 평면 terrain보다 입체감과 실루엣 변화가 강하다.

구면에서는 “높이”가 절대적인 위아래가 아니라 중심에서 멀어지는 정도다. 따라서 평면에서 작은 물결처럼 보이는 값도 구면에서는 행성 표면의 돌출과 함몰로 읽힌다.

## 좌표 선택

구면 terrain에서 가장 중요한 선택은 노이즈를 어떤 좌표로 샘플링하는가다.

### 위도/경도 UV 샘플링

위도/경도 방식은 구면 좌표를 2D로 펼친 뒤 2D 노이즈를 읽는다.

```text
u = longitude / 2pi
v = latitude / pi
height = noise2(u, v)
```

이 방식은 작성이 쉽지만 좌표계의 특이점이 있다.

- 경도는 극점에서 한 점으로 모인다.
- 같은 `u` 간격이 적도에서는 긴 거리이고 극점 근처에서는 짧은 거리다.
- 텍스처 seam이 생길 수 있다.
- 극점 주변 패턴이 눌리거나 회전축 주변으로 몰려 보일 수 있다.

즉 위도/경도 방식의 문제는 노이즈 자체보다 좌표 매핑에서 나온다.

### 3D 방향 벡터 샘플링

3D 방향 벡터 방식은 구면 위의 점을 그대로 3D 노이즈 필드에 넣는다.

```text
direction = normalize(vertex)
height = noise3(direction * frequency + seed)
```

이 방식은 UV를 만들지 않는다. 북극과 남극도 특별한 배열 인덱스가 아니라 3D 공간의 방향 벡터일 뿐이다. 그래서 위도/경도 방식의 극점 압축과 seam 문제가 직접 생기지 않는다.

직관적으로는 3D 공간 전체에 안개 같은 노이즈 필드가 있고, 그 안에 구를 넣은 뒤 구 표면에서 값을 읽는 것이다. 구 표면은 3D 필드의 얇은 껍질 단면이다.

## 왜 3D 샘플링도 평면과 다르게 보이는가

3D 방향 샘플링이 극점 왜곡을 줄여도, 평면 terrain과 똑같이 보이지는 않는다. 이유는 도메인과 기하가 다르기 때문이다.

첫째, 평면은 펼쳐진 사각형이고 구면은 닫힌 곡면이다. 구면에는 가장자리 seam이 없고, 패턴이 표면을 돌아 다시 만난다.

둘째, 구면에서는 거리 감각이 chord distance와 arc distance 사이에서 보인다. 노이즈 입력은 3D 좌표 차이를 사용하고, 표면 위에서 사람이 느끼는 거리는 구면 호 길이다. 작은 영역에서는 둘이 거의 같지만, 큰 feature에서는 평면과 다른 곡률감이 생긴다.

셋째, displacement 방향이 다르다. 평면은 모든 점이 같은 방향으로 올라가지만 구면은 모든 점이 각자의 radial 방향으로 올라간다. 그래서 높이 변화가 실루엣에도 직접 나타난다.

넷째, 조명 normal이 다르다. 구면의 기본 normal은 이미 위치마다 다르고, terrain displacement 후에는 삼각형 기하에 맞춰 normal을 다시 계산해야 한다. normal 차이는 시각적 인상에 큰 영향을 준다.

## Icosphere를 쓰는 이유

구면 메쉬를 만드는 대표 방식은 두 가지다.

### UV Sphere

UV sphere는 위도/경도 선으로 만든다.

- 구현이 쉽다.
- 극점에 많은 삼각형이 몰린다.
- 경도 seam이 있다.
- 위도별 삼각형 면적 차이가 크다.

### Icosphere

Icosphere는 정이십면체에서 시작해 각 삼각형을 나누고 다시 구면으로 정규화한다.

- 모든 면이 삼각형이다.
- 극점으로 특별히 몰리는 구조가 없다.
- UV seam이 필요 없다.
- 위도/경도 격자보다 면적 분포가 균일하다.

현재 구면 케이스가 `icosphere`를 쓰는 이유는 이것이다. 구면 terrain 특성을 보려는 실험에서 UV sphere의 극점 구조가 섞이면, 노이즈 문제와 메쉬 문제를 구분하기 어려워진다.

## 현재 구현의 데이터 흐름

현재 구면 케이스의 흐름은 다음과 같다.

```text
icosahedron 생성
삼각형 subdivision
각 vertex를 normalize해서 unit sphere 위로 이동
direction buffer를 GPU storage buffer로 업로드
compute shader dispatch
  direction 벡터를 3D fBm noise에 입력
  height 계산
  position = direction * (1 + height)
  tangent sampling으로 normal 계산
  terrain vertex buffer에 저장
기존 terrain 렌더 셰이더로 표시
```

현재 케이스의 기본값은 `subdivisions = 6`이고, 실험 상한은 8이다. `subdivisions = 8`은 약 1,310,720개 삼각형을 만들므로 높은 octave 관찰에는 유리하지만, 토폴로지 생성과 index buffer 업로드 비용도 커진다.

현재 compute shader 경로에서 CPU가 담당하는 부분은 `icosphere` 토폴로지 생성이다. GPU가 담당하는 부분은 각 vertex의 height, displaced position, normal 생성이다. 따라서 frequency, amplitude, octave, seed 변경은 topology를 다시 만들지 않고 compute shader만 다시 실행한다. subdivisions 변경은 vertex 수와 triangle 수 자체가 바뀌므로 CPU topology 생성과 GPU terrain 계산을 함께 다시 수행한다.

ModernGL 창은 카메라가 멈춰 있어도 렌더 루프를 계속 돈다. 그래서 고밀도 구면 mesh는 영상 재생이나 애니메이션이 없어도 GPU 사용량을 만들 수 있다. 현재 케이스는 입력 중에는 `active-fps`를 쓰고, 움직임이 없으면 `idle-fps`로 내려가도록 제한한다. 기본값은 active 60FPS, idle 12FPS다.

코드 위치:

```text
implementations/terrain_sphere_3d_noise/main_spherical_terrain_3d_noise.py
```

실행:

```powershell
uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py
```

통계만 출력:

```powershell
uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py --analyze-only
```

## 위도 밴드 통계 읽기

현재 패널과 `--analyze-only` 출력은 위도를 다섯 구간으로 나누어 height의 평균과 표준편차를 보여준다.

```text
south polar
south mid
equatorial
north mid
north polar
```

볼 것은 `std`다. `std`가 특정 극점 밴드에서 계속 작거나 크면, 그 영역의 height 변화가 다른 영역과 다르다는 뜻이다. 한 번의 seed에서는 우연한 차이가 생긴다. 여러 seed와 frequency에서 같은 경향이 반복되는지가 중요하다.

현재 기본값에서는 밴드별 표준편차가 대체로 비슷한 범위에 놓인다. 이것은 3D 방향 샘플링이 위도/경도 UV처럼 극점 압축을 직접 만들지 않는다는 첫 증거다.

통계를 더 엄밀하게 보려면 각 vertex를 동일 가중치로 세지 않고, vertex가 대표하는 면적을 가중치로 넣어야 한다. Icosphere는 UV sphere보다 균일하지만 완전한 equal-area 샘플링은 아니다.

## Frequency의 의미

평면에서 frequency는 단위 사각형 안에 노이즈 변화가 얼마나 자주 들어가는지를 뜻한다.

구면에서 현재 frequency는 unit sphere 방향 벡터에 곱해지는 값이다.

```text
noise3(direction * frequency)
```

frequency가 낮으면 구 전체에 큰 대륙 같은 덩어리가 생긴다. frequency가 높으면 표면에 작은 산맥과 요철이 늘어난다.

평면의 frequency와 구면의 frequency는 숫자가 같아도 시각적 크기가 완전히 같지 않다. 구면은 닫힌 곡면이고, 보는 방향마다 곡률과 실루엣이 달라지기 때문이다.

## fBm과 Octave

구면에서도 fBm 구조는 평면과 같다.

```text
height =
  noise3(direction * frequency)
  + persistence * noise3(direction * frequency * lacunarity)
  + persistence^2 * noise3(direction * frequency * lacunarity^2)
  + ...
```

다만 모든 octave가 같은 구면 방향 벡터에서 출발한다. 따라서 전체 패턴은 구면 전체에 연속적으로 이어진다. seam은 없다.

octave를 늘리면 작은 디테일이 증가한다. amplitude를 키우면 구의 반지름 대비 돌출이 커진다. amplitude가 너무 크면 행성 표면보다 가시 돋친 물체처럼 보인다.

## Normal과 조명

구면 terrain에서 normal은 특히 중요하다.

높이 변위 전의 normal은 간단하다.

```text
normal = direction
```

하지만 height를 적용한 뒤의 표면은 더 이상 완벽한 구가 아니다. 이때도 `direction`을 normal로 쓰면 조명이 너무 매끈하게 보인다. 산과 계곡의 기울기가 조명에 반영되지 않는다.

현재 창 렌더링 구현은 compute shader에서 각 vertex 주변의 tangent 방향과 bitangent 방향으로 height를 다시 샘플링하고, 그 두 방향의 기울기를 이용해 normal을 계산한다. 그래서 CPU가 face normal을 누적하지 않아도 산과 계곡의 기울기가 조명에 반영된다.

`--analyze-only` 통계 경로는 창을 열지 않기 때문에 기존 CPU 계산을 사용한다. 이 경로에서는 변위된 삼각형의 face normal을 만들고, 인접 face normal을 더해 vertex normal을 다시 계산한다.

## 3D Noise의 남는 한계

3D 방향 샘플링은 UV 극점 문제를 줄이지만 모든 문제가 사라지는 것은 아니다.

- 현재 3D gradient noise는 내부적으로 정수 cubic lattice를 쓴다.
- cubic lattice 기반 노이즈는 특정 조건에서 축 방향 artifact가 약하게 보일 수 있다.
- frequency가 낮거나 seed가 특정 패턴을 만들 때 방향성이 눈에 띌 수 있다.
- 이 문제는 도메인을 octave마다 회전하거나, simplex/open simplex 계열 3D 노이즈를 쓰면 줄일 수 있다.

즉 현재 케이스는 “구면 좌표 매핑 문제를 피한 방식”이지 “모든 방향 artifact가 원천적으로 없는 방식”은 아니다.

## Mesh-Domain Noise와의 차이

사용자가 앞서 말한 삼각형 메쉬 기반 노이즈는 다른 계열이다.

3D 방향 샘플링:

```text
구면 vertex direction을 3D noise field에 입력한다.
메쉬는 샘플 위치와 렌더링 표면 역할을 한다.
```

Mesh-domain noise:

```text
샘플 점이 어느 삼각형 안에 있는지 찾는다.
삼각형 vertex의 random value 또는 gradient를 가져온다.
barycentric coordinate로 보간한다.
```

3D 방향 샘플링은 구현이 단순하고 seam이 없다. Mesh-domain noise는 메쉬 topology와 직접 연결되므로 구면 subdivision, LOD, 판 구조, 지역별 biome 같은 제어에 더 적합하다.

## 공부할 때 볼 순서

1. `--analyze-only`로 기본 통계를 본다.
2. 실행 창에서 wireframe을 켜고 icosphere 삼각형 분포를 본다.
3. `frequency`를 낮춰 큰 대륙형 패턴을 본다.
4. `frequency`를 높여 작은 요철이 구면에서 어떻게 보이는지 본다.
5. `amplitude`를 키워 radial displacement가 실루엣에 미치는 영향을 본다.
6. `seed`를 바꿔 위도 밴드 통계가 한 seed의 우연인지 반복 경향인지 본다.
7. `subdivisions`를 낮춰 메쉬 해상도가 낮을 때 noise가 어떻게 계단처럼 보이는지 본다.
8. `subdivisions`를 7 또는 8로 올려 높은 octave 디테일을 더 촘촘한 vertex 샘플로 표현해 본다.

## 오른쪽 상단 좌표 표시기

실행 화면 오른쪽 상단에는 작은 구면 좌표 표시기가 있다. 이것은 지형 자체를 다시 그리는 미니맵이 아니라, 현재 카메라에서 구면 좌표 기준이 어떻게 보이는지 알려주는 orientation gizmo다.

현재 좌표 기준은 다음과 같다.

```text
north pole = +Y
longitude 0 = +X on equator
longitude +90 = +Z on equator
longitude -90 = -Z on equator
```

표시기 안의 `N`은 북극이다. `0`, `+90`, `-90`은 각각 적도 위의 기준 경도 방향이다. 경선은 앞쪽 반구에서는 밝게, 뒤쪽 반구에서는 흐리게 그린다. 그래서 카메라를 회전하면 어떤 기준 경선이 앞쪽으로 왔는지, 북극이 화면에서 어느 방향으로 기울었는지 바로 볼 수 있다.

`view`는 현재 카메라 위치를 구면 방향으로 환산한 경도/위도 값이다. 이 값은 지형의 물리 좌표가 바뀌었다는 뜻이 아니라, 사용자가 어느 방향에서 구를 보고 있는지 나타내는 보기 좌표다.

## 질문과 답변 기록

### Q. 3D 노이즈 샘플링을 쓰면 적도와 극점에서 특성이 달라지는가?

위도/경도 UV로 2D 노이즈를 샘플링하면 적도와 극점의 특성이 달라진다. 같은 `u` 간격이 적도에서는 넓은 표면 거리를 뜻하고, 극점 근처에서는 좁은 표면 거리를 뜻하기 때문이다. 극점에서는 경도가 한 점으로 모이는 특이점도 생긴다.

현재 구면 케이스는 UV를 쓰지 않고 3D 방향 벡터를 사용한다.

```text
height = noise3(normalize(position) * frequency)
```

이 방식에서는 북극과 남극이 특별한 UV 좌표가 아니라 3D 공간의 방향 벡터다. 따라서 UV 매핑 때문에 생기는 극점 압축은 직접 나타나지 않는다. 다만 유한한 메쉬 샘플 수, icosphere 면적 분포, 3D cubic lattice noise의 약한 축 방향성은 별도로 남을 수 있다.

### Q. 현재 스피어 terrain은 여러 레이어를 갖는가?

현재 스피어 terrain은 평면 terrain generator처럼 레이어 스택을 갖지 않는다. 구조는 단일 fBm 레이어다.

```text
sphere terrain = one fBm noise layer
one fBm layer = multiple octaves
```

따라서 `octaves`는 있다. 하지만 `Simple + Valley + Warped`처럼 여러 레이어를 더하는 구조는 아직 없다.

### Q. Subdivision은 구면을 몇 등분한다는 뜻인가?

아니다. `subdivisions = 5`는 구면을 5등분한다는 뜻이 아니다. Icosphere는 정이십면체에서 시작한다.

```text
subdivisions 0: 20 triangles
subdivisions 1: 80 triangles
subdivisions 2: 320 triangles
subdivisions 3: 1,280 triangles
subdivisions 4: 5,120 triangles
subdivisions 5: 20,480 triangles
subdivisions 6: 81,920 triangles
subdivisions 7: 327,680 triangles
subdivisions 8: 1,310,720 triangles
```

Subdivision은 각 삼각형을 네 개로 쪼개는 반복 횟수다. 평면 terrain의 `resolution`과 비슷하게, 구면 terrain에서는 기하 샘플 밀도를 정한다.

### Q. Subdivision과 octave는 같이 올려야 하는가?

그렇다. `octaves`는 노이즈가 만들려는 작은 디테일의 수를 늘린다. `subdivisions`는 그 디테일을 실제 구면 메쉬가 표현할 수 있는 샘플 수를 늘린다.

Octave만 올리고 subdivision이 낮으면 작은 디테일이 vertex 샘플에 잡히지 않는다. 이 경우 삼각형 단위로 어색한 요철, 계단감, 반짝임이 생길 수 있다.

현재 감각은 다음과 같다.

```text
subdivisions 4: 낮은 octave 관찰용
subdivisions 5: 중간 octave 관찰용
subdivisions 6: 기본값, octave 5 전후 관찰용
subdivisions 7: 더 높은 디테일 관찰용
subdivisions 8: 고밀도 실험용
```

### Q. 삼각형 내부에도 terrain 샘플을 찍는가?

현재 구현은 삼각형 내부에 별도 샘플을 찍지 않는다. Subdivision으로 만들어진 fine mesh의 vertex가 샘플링 포인트다.

```text
sample point = each icosphere vertex direction
```

각 vertex에서 3D noise를 샘플링하고, 그 height로 vertex를 radial 방향으로 이동한다. 삼각형 내부는 GPU rasterizer가 세 vertex 사이를 선형 보간해서 채운다. 따라서 렌더 triangle 자체가 현재 terrain 기하의 최소 단위다.

삼각형 내부까지 더 세밀하게 샘플링하려면 GPU tessellation shader, compute 기반 mesh 생성, 더 높은 CPU subdivision, 또는 fragment shader 기반 시각 효과가 필요하다.

### Q. Subdivision 6도 샘플 수가 작은가?

평면 512x512 terrain과 비교하면 작다.

```text
sphere subdivisions 6: vertices 40,962 / triangles 81,920
plane 512x512: vertices 262,144 / triangles 522,242
```

그래서 복잡한 octave 지형을 보려면 subdivision 7 또는 8이 필요할 수 있다. 현재 케이스는 UI와 명령행에서 최대 8까지 허용한다.

### Q. 화면이 멈춰 있는데 GPU를 쓰는 이유는 무엇인가?

ModernGL 창은 화면 변화가 없어도 렌더 루프를 계속 돈다. 스피어 terrain은 매 프레임 전체 구면 mesh와 ImGui overlay를 다시 그린다. `subdivisions = 8`은 약 131만 triangle이므로, 정지 화면이어도 60FPS로 계속 렌더링하면 GPU 사용량이 높게 나온다.

현재 구현은 이 문제를 줄이기 위해 FPS cap을 둘로 나눈다.

```text
active-fps = 입력 중 cap
idle-fps = 움직임이 없을 때 cap
```

기본값은 active 60FPS, idle 12FPS다. 패널에는 현재 cap이 `Cap: 60` 또는 `Cap: 12`로 표시된다.

명령행에서 조절할 수 있다.

```powershell
uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py --active-fps 60 --idle-fps 8
```

### Q. Tessellation shader와 compute shader는 무엇이 다른가?

둘 다 GPU를 쓰지만 GPU를 쓰는 위치가 다르다.

```text
Tessellation shader = 렌더링 파이프라인 안에서 삼각형을 더 잘게 쪼개는 단계
Compute shader = 렌더링 파이프라인 밖에서 실행하는 범용 병렬 계산
```

Tessellation shader는 화면에 그리는 과정 안에 들어 있다.

```text
CPU coarse mesh
  -> vertex shader
  -> tessellation control shader
  -> tessellation primitive generator
  -> tessellation evaluation shader
  -> fragment shader
  -> screen
```

이 방식은 “지금 그릴 triangle을 화면에서 더 촘촘하게 만든다”는 목적에 특화되어 있다. 구면 terrain에서는 낮은 해상도 icosphere triangle을 넣고, GPU가 triangle 내부를 세분화한 뒤, 새 점을 normalize해서 구면 위로 올리고, 그 위치에서 3D noise를 샘플링해 radial displacement를 적용할 수 있다.

Compute shader는 렌더링 파이프라인 바깥에 있다.

```text
CPU parameters
  -> compute shader dispatch
  -> GPU buffer / texture / SSBO에 결과 저장
  -> render pass가 그 결과 buffer를 읽어 그림
  -> screen
```

이 방식은 렌더링 전용 단계가 아니라 GPU에서 실행하는 일반 병렬 작업에 가깝다. CPU 코드의 병렬 for-loop처럼 생각할 수 있다.

```text
for each vertex index on GPU:
    direction 계산
    noise 계산
    height 적용
    normal 계산
    output buffer에 저장
```

두 방식의 차이를 정리하면 다음과 같다.

| 구분 | Tessellation shader | Compute shader |
|---|---|---|
| 위치 | 렌더링 파이프라인 안 | 렌더링 파이프라인 밖 |
| 성격 | 표면 세분화에 특화 | 범용 병렬 계산 |
| subdivision | 매우 자연스러움 | 가능하지만 직접 설계 |
| noise 계산 | evaluation shader에서 가능 | compute 작업으로 가능 |
| 결과 저장 | 기본적으로 렌더링 중 임시 결과 | buffer/texture에 명시 저장 |
| export/재사용 | 상대적으로 불편 | 상대적으로 자연스러움 |
| LOD | 카메라 거리 기반으로 자연스러움 | 가능하지만 직접 구현 |
| 사고방식 | “그릴 때 더 촘촘히 그린다” | “GPU에서 데이터를 만들어 저장한다” |

현재 스피어 terrain은 compute shader 방식을 선택했다. subdivision된 vertex direction을 입력 buffer로 넣고, compute shader가 noise height, displaced position, normal을 terrain vertex buffer에 저장한다. 이 결과 buffer를 렌더링과 export 양쪽에 쓸 수 있기 때문이다. Tessellation shader는 구면 표면을 실시간으로 촘촘하게 그리는 데 강하지만, 생성된 데이터를 파일이나 분석용 배열로 다루려면 별도 readback 구조가 필요하다.

### Q. 오른쪽 상단 구면 표시기는 무엇을 보여주는가?

오른쪽 상단 표시기는 지형 미니맵이 아니라 orientation gizmo다. 구면 좌표 기준이 현재 카메라에서 어떻게 보이는지 알려준다.

```text
N = north pole = +Y
0 = longitude 0 = +X
+90 = longitude +90 = +Z
-90 = longitude -90 = -Z
```

`view`는 현재 카메라 방향을 구면 경도/위도로 환산한 값이다. 시작점 대비 변화량인 `delta` 표시는 의미가 중복되어 제거했다.

## 요약

평면 terrain과 구면 terrain의 가장 큰 차이는 노이즈 함수보다 도메인이다. 평면은 사각형 도메인에 전역 높이축을 둔다. 구면은 닫힌 곡면에 지점별 radial 높이축을 둔다.

3D 방향 벡터 샘플링은 구면 terrain에서 가장 단순하고 강한 기본 방법이다. 위도/경도 UV의 극점 압축과 seam을 피하면서도 구 전체에 연속적인 지형을 만든다. 다만 메쉬 분포, normal 계산, 3D noise lattice artifact, frequency 해석은 별도로 관찰해야 한다.

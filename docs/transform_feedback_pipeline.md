# Transform Feedback Pipeline

## 목적

Transform feedback은 GPU 셰이더가 계산한 값을 화면에 바로 그리지 않고 GPU 버퍼에 다시 저장하는 OpenGL 기능이다. 이 프로젝트에서는 terrain bake, contour extraction, Marching Cubes, legacy voxel instancing 논의에서 같은 용어가 반복해서 나온다.

이 문서는 transform feedback이 무엇인지, 일반 렌더링과 무엇이 다른지, 이 프로젝트의 각 구현에서 어떤 역할을 하는지 정리한다.

## 한 줄 정의

Transform feedback은 다음 작업이다.

```text
GPU shader output -> GPU buffer
```

보통 셰이더의 출력은 rasterization과 fragment shader를 거쳐 화면 픽셀이 된다. transform feedback은 그 중간에서 vertex shader 또는 geometry shader의 출력 값을 잡아 GPU buffer에 저장한다. 그래서 셰이더를 "그리는 도구"가 아니라 "데이터를 만드는 도구"처럼 사용할 수 있다.

## 일반 렌더링과의 차이

일반 렌더링 흐름은 다음과 같다.

```text
vertex shader
-> geometry shader
-> rasterization
-> fragment shader
-> framebuffer / screen
```

Transform feedback 흐름은 다음과 같다.

```text
vertex shader
-> geometry shader
-> transform feedback buffer
```

이때 결과는 화면이 아니라 VBO 같은 GPU buffer에 남는다. 이후 그 buffer를 다시 vertex attribute로 연결하면, CPU로 데이터를 가져오지 않고 바로 렌더링할 수 있다.

## ModernGL에서 보이는 형태

ModernGL 코드에서는 보통 세 요소가 함께 나타난다.

```python
program = ctx.program(
    vertex_shader=...,
    geometry_shader=...,
    varyings=["out_pos", "out_normal", "out_height"],
)

target_buffer = ctx.buffer(reserve=...)
vao.transform(target_buffer, vertices=count)
```

`varyings`는 buffer에 저장할 셰이더 출력 변수 이름이다. `vao.transform(...)`은 화면 렌더링 대신 transform feedback pass를 실행한다. 즉, 셰이더가 내보내는 `out_pos`, `out_normal`, `out_height` 값이 순서대로 target buffer에 들어간다.

## 왜 쓰는가

이 프로젝트에서 transform feedback을 쓰는 이유는 CPU-GPU 왕복을 피하기 위해서다.

CPU에서 큰 메시를 만들면 다음 비용이 생긴다.

```text
CPU 계산
-> 큰 vertex/index 배열 생성
-> GPU로 업로드
-> 렌더링
```

Transform feedback을 쓰면 다음 흐름이 가능하다.

```text
GPU 계산
-> GPU buffer에 저장
-> 같은 GPU buffer를 렌더링에 사용
```

따라서 대량의 vertex를 매번 CPU에서 만들어 업로드하지 않아도 된다.

## 이 프로젝트의 사용 사례

### 1. GPU 평면 Terrain Bake

GPU 평면 terrain generator는 grid sample마다 height와 normal을 GPU에서 계산한 뒤 transform feedback으로 정적 VBO에 굽는다.

```text
uv grid vertex
-> terrain_bake.vert
-> out_pos, out_normal, out_height
-> terrain VBO
-> render shader로 표시
```

여기서는 geometry shader가 필요 없다. vertex shader가 입력 vertex 하나를 출력 vertex 하나로 바꾸고, 그 결과를 VBO에 저장한다. 레이어를 수정하거나 resolution을 바꿀 때 다시 굽는다.

### 2. GPU Marching Squares

Marching Squares는 2D density field에서 threshold를 지나는 등고선 선분을 만든다.

```text
grid cell point
-> vertex shader
-> geometry shader에서 case 판단
-> contour segment vertices
-> transform feedback buffer
-> line render
```

여기서는 한 cell이 선분 0개, 1개, 또는 여러 개를 만들 수 있다. 그래서 geometry shader가 필요하다.

### 3. GPU Marching Cubes

Marching Cubes는 3D density field에서 threshold를 지나는 등가면 삼각형을 만든다.

```text
voxel cell point
-> vertex shader에서 cell 위치 계산
-> geometry shader에서 8개 corner density 샘플
-> triTable 조회
-> 최대 5개 triangle, 15개 vertex emit
-> transform feedback buffer
-> triangle render
```

Marching Cubes에서 transform feedback은 "voxel cell들을 검사해서 실제 표면 삼각형만 GPU buffer에 굽는 단계"다. 결과 buffer는 이미 최종 렌더링 가능한 triangle vertex 배열이다.

### 4. 삭제된 Legacy Voxel Instancing

`gpu_voxel_instancing_legacy`는 Marching Cubes 이전에 쓰던 중간 단계였다. Python 실행 코드 없이 shader만 남아 있었고, 현재는 삭제했다.

당시 구조는 다음에 가까웠다.

```text
voxel grid point
-> shader에서 solid 여부와 주변 노출 여부 판단
-> 보이는 voxel center만 transform feedback buffer에 저장
-> cube mesh를 instancing으로 렌더링
```

즉 legacy 방식의 결과물은 최종 표면 삼각형이 아니라 "큐브를 그릴 voxel 후보 목록"이었다. Marching Cubes가 들어온 뒤에는 이 방식의 활용 가치가 낮아졌고, 현재 유효 구현 목록에서 제거했다.

## Terrain Bake와 Marching Cubes의 차이

둘 다 transform feedback을 쓰지만 생성되는 데이터의 성격이 다르다.

| 구현 | 입력 하나가 만드는 출력 | 결과 buffer |
| --- | --- | --- |
| GPU 평면 terrain bake | vertex 1개 | 같은 grid 구조의 heightfield vertex |
| Marching Squares | line segment 0개 이상 | 등고선 vertex |
| Marching Cubes | triangle 0~5개 | 등가면 triangle vertex |
| 삭제된 legacy voxel instancing | voxel 후보 0개 또는 1개 | cube instance 위치 |

평면 terrain은 "기존 grid의 속성을 채우는 bake"에 가깝다. Marching Cubes는 "입력 cell에서 새로운 기하를 생성하는 extraction"에 가깝다.

## Compute Shader와의 차이

Compute shader도 GPU에서 데이터를 만들 수 있다. 차이는 파이프라인 위치와 사용 감각이다.

| 구분 | Transform feedback | Compute shader |
| --- | --- | --- |
| 위치 | 렌더링 파이프라인 안 | 렌더링 파이프라인 바깥 |
| 주 입력 | vertex/primitive stream | 임의 buffer, texture, work group |
| 출력 | shader varying을 buffer에 기록 | storage buffer/image 등에 기록 |
| 장점 | vertex/geometry shader 결과를 곧바로 VBO처럼 쓰기 좋음 | 일반 계산, 임의 write, 복잡한 병렬 작업에 유리 |
| 한계 | 출력 구조가 vertex stream에 묶임 | 렌더링용 VAO/VBO 연결을 별도로 설계해야 함 |

이 프로젝트의 스피어 terrain은 compute shader를 사용한다. 스피어 terrain은 subdivision과 layer height 계산을 더 일반적인 GPU 계산 문제로 다루므로 compute shader 쪽이 자연스럽다. 반대로 Marching Cubes의 현재 구현은 geometry shader가 cell별 삼각형을 emit하고 transform feedback으로 잡는 구조가 이미 맞아 있다.

## 삭제 기록과 보존 기준

`gpu_smoke_test`와 `gpu_voxel_instancing_legacy`는 삭제했다.

삭제 판단은 다음과 같다.

```text
gpu_smoke_test: ModernGL 환경 확인용 삼각형 테스트였고 현재 기능 경로가 아니므로 삭제
gpu_voxel_instancing_legacy: 실행 코드 없이 shader만 남아 있었고 Marching Cubes가 후속 방식이므로 삭제
gpu_marching_cubes: transform feedback의 현재 유효 사용처
terrain_gpu_generator_plane: transform feedback의 현재 유효 사용처
gpu_marching_squares: transform feedback의 현재 유효 사용처
```

남길 가치가 있는 transform feedback 설명은 삭제된 legacy shader 폴더보다 이 문서와 실제 작동 코드에 있다.

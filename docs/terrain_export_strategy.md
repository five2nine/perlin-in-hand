# Terrain Export Strategy

## 결정

평면 terrain generator와 스피어 terrain generator는 모두 Hybrid export를 사용한다.

```text
Hybrid export = recipe + baked result
```

이 방식은 생성 규칙과 표시 결과를 함께 저장한다. Viewer는 baked result를 바로 읽어 표시하고, generator는 나중에 import 기능을 붙였을 때 recipe로 레이어 스택을 복원할 수 있다.

## Recipe

Recipe는 생성 의도를 담는다.

- generator type
- backend
- resolution 또는 subdivisions
- palette
- layer stack
- layer kind, octaves, frequency, amplitude, persistence, lacunarity
- valley, warp, seed, enabled 상태

Recipe만 저장하면 파일은 작지만, 나중에 shader 코드나 hash 함수가 바뀌었을 때 같은 결과를 보장하기 어렵다.

## Baked Result

Baked result는 현재 화면에 그려지는 결과 메시를 담는다.

- vertices
- positions
- normals
- heights
- indices
- vertex layout
- mesh shape 또는 grid shape

Baked result만 저장하면 viewer가 단순해지고, 나중에 생성 알고리즘이 바뀌어도 같은 메시를 볼 수 있다. 하지만 생성 의도와 레이어 편집 상태를 잃는다.

## 평면 Terrain Export

평면 generator는 `heightfield_plane` recipe와 baked grid mesh를 함께 저장한다.

```text
recipe:
  generator_type = heightfield_plane
  resolution
  palette
  layers[]

baked:
  vertices = resolution * resolution
  indices = grid triangle indices
  grid_shape = [resolution, resolution]
```

CPU 버전은 CPU에서 계산해 업로드한 VBO를 읽는다. GPU 버전은 transform feedback으로 구운 VBO를 읽는다. Transform feedback 자체의 의미는 [transform_feedback_pipeline.md](transform_feedback_pipeline.md)에 정리한다.

## 스피어 Terrain Export

스피어 generator는 `sphere_terrain` recipe와 baked sphere mesh를 함께 저장한다.

```text
recipe:
  generator_type = sphere_terrain
  subdivisions
  subdivision_steps
  gpu_subdivision_mode = non_indexed_triangle_list
  palette
  layers[]

baked:
  vertices = draw_vertices
  indices = sequential triangle indices
  mesh_shape = [draw_vertices]
  topology = non_indexed_triangle_list
```

현재 스피어 terrain은 GPU compute shader가 정이십면체 base triangle을 직접 subdivision하고 non-indexed triangle list를 만든다. 따라서 export 파일도 draw vertex 배열과 순차 triangle index를 저장한다.

## 레이어별 Baked Data

레이어별 height 결과는 기본 export에 저장하지 않는다. 레이어가 많고 해상도나 subdivisions가 높으면 파일 크기가 크게 늘기 때문이다.

레이어별 baked data는 기본 포맷이 아니라 디버그 export 옵션으로 분리하는 편이 맞다.

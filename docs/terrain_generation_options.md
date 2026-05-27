# Terrain Generation Options

이 문서는 정적 지형 생성 유틸리티에서 사용자가 선택할 수 있는 옵션과 옵션끼리의 관계를 설명한다.

CPU 버전과 GPU 버전은 같은 레이어 스택 모델을 사용한다. 각 레이어는 `height = f(x, y)` 형태의 2D 높이장을 만들고, 여러 레이어를 더해 최종 지형을 만든다.

## 레이어 스택

지형은 하나의 큰 설정값으로 만들어지는 것이 아니라 여러 레이어를 누적해서 만든다.

- `enabled`: 레이어를 켜거나 끈다. 꺼진 레이어는 스택에 남아 있지만 높이 계산에는 들어가지 않는다.
- `Del`: 레이어를 스택에서 제거한다.
- `selected layer`: 아래 속성 패널에서 편집할 레이어다.
- `Reset Terrain`: 기본 Simple 1 octave 레이어 하나만 있는 상태로 돌아간다.

레이어를 추가하면 종류와 일부 값이 랜덤으로 정해진다. 이후 선택 레이어 속성에서 octaves, frequency, amplitude, warp 값 등을 직접 바꿀 수 있다.

## 추가 버튼

상단 레이어 추가 버튼은 빠르게 시작점을 만드는 프리셋이다.

- `Random`: 종류, octaves, frequency, amplitude, persistence, lacunarity, valley, warp 값을 모두 랜덤으로 만든다.
- `1 Oct`, `2 Oct`, `3 Oct`: Simple 레이어를 해당 octave로 추가한다. 나머지 값은 랜덤이다.
- `Valley`: Valley 레이어를 추가한다. octaves와 나머지 값은 랜덤이다.
- `Billow`: Billow 레이어를 추가한다. octaves와 나머지 값은 랜덤이다.
- `Ridged`: Ridged 레이어를 추가한다. octaves와 나머지 값은 랜덤이다.
- `Warped`: Warped 레이어를 추가한다. octaves와 나머지 값은 랜덤이고, warp strength가 켜진 상태로 시작한다.

이 구조의 의도는 작은 버튼 묶음으로 대표적인 지형 성격을 빠르게 만들고, 자세한 수치는 선택 레이어 속성에서 조정하는 것이다.

## 지형 종류

모든 지형 종류는 같은 레이어 데이터 구조를 사용한다. 따라서 UI에는 같은 속성들이 보인다. 다만 종류마다 높이장을 만드는 방식이 다르므로 같은 속성이라도 체감 효과가 다르다.

### Simple

기본 노이즈 레이어다.

- 1 octave에서는 단일 노이즈 필드를 만든다.
- 2 또는 3 octave에서는 여러 주파수의 노이즈를 누적해 더 복잡한 표면을 만든다.
- 가장 중립적인 시작점이다.

### Valley

협곡과 골짜기 성격을 만드는 레이어다.

- fBm 기반 값을 골짜기 형태로 변환한다.
- `valley_power`가 직접 영향을 준다.
- 값이 강하면 깊고 좁은 골짜기 쪽으로 간다.

### Billow

둥근 봉우리나 부풀어 오른 표면을 만드는 레이어다.

- fBm 값의 절댓값 계열 변환을 사용한다.
- 높낮이가 부드럽게 반복되는 느낌을 만든다.

### Ridged

능선과 날카로운 산줄기를 만드는 레이어다.

- fBm 값을 ridge 형태로 뒤집어 변환한다.
- 산맥의 선, 접힌 지형, 날카로운 능선을 만들 때 유용하다.

### Warped

좌표가 휘어진 지형을 만드는 레이어다.

- 기본 샘플링 전에 `warp_strength`와 `warp_frequency`로 좌표를 흔든다.
- 뒤틀린 산맥, 흐르는 듯한 패턴, 비대칭 지형을 만들 때 유용하다.
- 현재 구현에서는 warp 값이 0보다 크면 다른 종류의 레이어에도 좌표 워핑이 적용될 수 있다. Warped 버튼은 이 warp 값을 의도적으로 켠 상태로 시작하는 프리셋이다.

## 선택 레이어 속성

아래 속성 패널은 선택된 레이어 하나를 편집한다. 모든 레이어가 같은 속성 세트를 갖기 때문에, 패널도 모든 값을 보여준다.

### Octaves

노이즈를 몇 겹 누적할지 정한다.

- 1: 가장 단순하고 읽기 쉬운 형태다.
- 2: 중간 규모와 세부 규모가 같이 들어간다.
- 3: 더 복잡하고 세밀한 형태가 된다.
- 4~6: 더 높은 주파수 디테일을 추가한다. 해상도나 subdivisions가 낮으면 작은 디테일이 제대로 샘플되지 않을 수 있다.

octaves는 지형의 성격을 크게 바꾸는 축이다. 그래서 `1 Oct`, `2 Oct`, `3 Oct` 버튼은 octaves만 명확히 고정하고 나머지를 랜덤으로 둔다. 선택 레이어의 `Octaves` 슬라이더는 최대 6까지 조정할 수 있다. Random 프리셋은 기본 관찰이 너무 촘촘해지지 않도록 1~3 octave 범위에서 시작한다.

### Frequency

패턴의 공간 주파수다.

- 낮으면 넓고 큰 지형 변화가 나온다.
- 높으면 촘촘하고 잦은 변화가 나온다.

### Amplitude

해당 레이어가 최종 높이에 더하는 힘이다.

- 낮으면 미세한 표면 디테일이 된다.
- 높으면 지형 전체 높낮이에 크게 영향을 준다.

### Persistence

octave가 올라갈 때 세부 노이즈의 세기가 얼마나 유지되는지 정한다.

- 낮으면 높은 octave의 영향이 빨리 줄어든다.
- 높으면 세부 노이즈가 더 강하게 남는다.

### Lacunarity

octave가 올라갈 때 주파수가 얼마나 빨리 증가하는지 정한다.

- 낮으면 octave끼리 비슷한 크기의 패턴을 만든다.
- 높으면 각 octave가 더 다른 크기의 패턴을 만든다.

### Valley Power

Valley 레이어의 골짜기 형태를 조절한다.

- 낮으면 넓고 완만한 골짜기가 된다.
- 높으면 좁고 깊은 골짜기가 된다.

이 값은 Valley 종류에서 직접적인 의미가 가장 크다.

### Warp Strength

샘플링 좌표를 얼마나 강하게 휘게 할지 정한다.

- 0이면 워핑이 없다.
- 값이 커질수록 패턴이 더 많이 뒤틀린다.

Warped 레이어는 이 값을 켠 상태로 시작한다. 다른 레이어도 이 값을 올리면 워핑된 Simple, 워핑된 Valley, 워핑된 Ridged처럼 사용할 수 있다.

### Warp Frequency

워핑 자체의 주파수다.

- 낮으면 큰 흐름으로 휘어진다.
- 높으면 더 촘촘한 뒤틀림이 생긴다.

`warp_strength`가 0이면 이 값은 눈에 보이는 효과가 없다.

## 전역 옵션

### Resolution

지형 그리드 해상도다. 값을 바꾸면 현재 레이어 스택 전체를 새 해상도로 다시 계산한다.

- GPU 버전은 transform feedback으로 새 VBO를 다시 굽는다.
- CPU 버전은 모든 높이와 노멀을 CPU에서 다시 계산해 VBO에 업로드한다.

Transform feedback의 의미와 이 프로젝트의 다른 사용처는 [transform_feedback_pipeline.md](transform_feedback_pipeline.md)에 정리한다.

CPU 버전에서는 높은 해상도와 많은 레이어를 함께 쓰면 조작 중 멈춘 것처럼 느껴질 수 있다. 이 경우 해상도를 낮추거나 레이어 수를 줄이는 편이 좋다.

### Palette

높이와 조명 결과를 어떤 색으로 보여줄지 정한다. 지형 형태나 레이어 계산은 바꾸지 않는다.

### Reset Camera

카메라 위치와 각도를 기본 보기로 되돌린다. 지형 데이터는 바꾸지 않는다.

### Export

현재 지형 상태를 `exports/terrain_generation/*.npz` 파일로 저장한다.

파일에는 recipe와 baked result가 함께 들어간다. 이 저장 정책은 [terrain_export_strategy.md](terrain_export_strategy.md)에 정리한다.

- `vertices`: `(resolution * resolution, 7)` float32 배열이다. 열 순서는 `pos_x, pos_y, pos_z, normal_x, normal_y, normal_z, height`다.
- `positions`: `(resolution * resolution, 3)` float32 위치 배열이다.
- `normals`: `(resolution * resolution, 3)` float32 노멀 배열이다.
- `heights`: `(resolution * resolution,)` float32 높이 배열이다.
- `indices`: `(triangle_count, 3)` uint32 삼각형 인덱스 배열이다.
- `metadata_json`: backend, resolution, palette, vertex/index layout, recipe, baked 배열 이름, 레이어 종류와 속성 값을 담은 JSON 문자열이다.

CPU 버전은 CPU에서 계산해 업로드한 현재 VBO를 읽어서 저장한다. GPU 버전은 transform feedback으로 구워진 현재 VBO를 읽어서 저장한다. 따라서 export 파일은 현재 화면에 렌더링되는 메시 데이터를 다른 프로그램에서 다시 읽기 위한 결과물이다.

## Legacy Matplotlib Viewer

Export 파일은 legacy Matplotlib 뷰어로 바로 확인할 수 있다.

```powershell
uv run .\implementations\terrain_legacy_viewer_matplotlib\main_terrain_legacy_viewer_matplotlib.py
```

경로를 생략하면 `exports/terrain_generation`에서 가장 최근 `.npz` 파일을 연다. 특정 파일을 열 때는 파일 경로를 인자로 넘긴다.

```powershell
uv run .\implementations\terrain_legacy_viewer_matplotlib\main_terrain_legacy_viewer_matplotlib.py .\exports\terrain_generation\terrain_gpu_512_20260526_225249.npz
```

뷰어는 `.npz` 안의 `metadata_json`에서 `grid_shape` 또는 `resolution`을 먼저 읽는다. 예전 export 파일처럼 해당 값이 없으면 `heights` 또는 `vertices`의 길이가 정사각형인지 확인해 `(sqrt(n), sqrt(n))` 형태로 추정한다. 따라서 현재 export 포맷에서는 데이터 형상을 판단할 수 있다.

heightmap은 그리드 인덱스 좌표를 사용한다. 512 해상도 파일은 축이 `0..511`로 표시된다. 3D surface는 기본적으로 export된 메시 월드 좌표를 사용한다. 현재 지형 메시의 월드 좌표는 `x=-0.5..0.5`, `z=-0.5..0.5` 범위 안에 512x512 샘플이 들어간 형태다. 3D surface도 그리드 인덱스 좌표로 보고 싶으면 `--surface-coords grid`를 사용한다.

기본 뷰어는 3D surface도 전체 해상도로 그린다. 512 해상도 파일은 512x512 surface 샘플을 표시한다. Matplotlib의 기본 surface 제한을 피하기 위해 뷰어는 `rstride=1`, `cstride=1`을 명시한다.

큰 지형은 3D surface를 그릴 때 느릴 수 있으므로 사용자가 원할 때 `--stride`로 샘플 간격을 조절한다.

```powershell
uv run .\implementations\terrain_legacy_viewer_matplotlib\main_terrain_legacy_viewer_matplotlib.py --stride 8
```

## Legacy pygame-ce NPZ Viewer

Export 파일은 legacy pygame-ce 기반 CPU 뷰어로도 확인할 수 있다.

```powershell
uv run .\implementations\terrain_legacy_viewer_pygame\main_terrain_legacy_viewer_pygame.py
```

이 뷰어는 export 파일의 `heights` 배열을 CPU에서 색상화한 뒤 Pygame surface로 표시한다. 지형을 3D 메시로 다시 렌더링하지 않고 2D heightmap을 빠르게 보는 용도다. 창 크기를 바꿔도 이미지는 비율을 유지하고, 마우스 드래그로 pan, 마우스 휠 또는 `+`/`-`로 zoom, `C`로 palette, `R`로 view reset을 수행한다.

경로를 생략하면 `exports/terrain_generation`에서 가장 최근 `terrain_cpu_*.npz`, `terrain_gpu_*.npz`, `terrain_sphere_*.npz` 파일을 연다. 특정 파일을 열 때는 파일 경로를 인자로 넘긴다.

```powershell
uv run .\implementations\terrain_legacy_viewer_pygame\main_terrain_legacy_viewer_pygame.py .\exports\terrain_generation\terrain_gpu_512_20260526_231238.npz
```

GPU 기반 terrain toolchain의 표준 뷰어는 `terrain_gpu_viewer`다. pygame-ce 뷰어와 Matplotlib 뷰어는 `terrain_legacy_*` 이름의 legacy 도구로 분리해 둔다. legacy 뷰어들은 `terrain_legacy_common/terrain_npz_loader.py`를 통해 `.npz` 데이터 형상을 읽으며, GPU toolchain의 정식 구성 요소로 다루지 않는다.

## GPU NPZ Viewer

Export 파일은 별도 GPU 뷰어로도 확인할 수 있다.

```powershell
uv run .\implementations\terrain_gpu_viewer\main_terrain_gpu_viewer.py
```

경로를 생략하면 `exports/terrain_generation`에서 가장 최근 `terrain_cpu_*.npz`, `terrain_gpu_*.npz`, `terrain_sphere_*.npz` 파일을 연다. 특정 파일을 열 때는 파일 경로를 인자로 넘긴다.

```powershell
uv run .\implementations\terrain_gpu_viewer\main_terrain_gpu_viewer.py .\exports\terrain_generation\terrain_gpu_512_20260526_231238.npz
```

GPU 뷰어는 export 파일의 `vertices`와 `indices`를 그대로 GPU 버퍼에 올리고, 지형 생성기가 쓰는 `terrain_heightfield.vert/frag` 렌더 셰이더를 재사용한다. 따라서 Matplotlib 뷰어보다 제너레이터의 화면 성능과 표현에 가깝다.

뷰어의 빛 위치는 모델 타입별 제너레이터 화면을 재현하는 쪽으로 맞춘다. 평면 terrain은 평면 제너레이터의 light position을 쓰고, sphere terrain은 스피어 제너레이터의 light position을 쓴다.

창 좌측의 `Loaded Terrain` 패널은 로딩된 파일 경로와 기본 사양을 표시한다. 표시 항목은 grid 또는 mesh 형태, vertex 수, triangle 수, height 범위, backend, layer 수, palette, light 기준, FPS다. 패널은 ImGui 창이므로 접거나 이동할 수 있고, 패널 위에서 마우스를 조작하면 카메라 회전/줌과 충돌하지 않는다.

`Load Model` 메뉴는 프로그램을 닫지 않고 다른 export 파일을 읽기 위한 메뉴다. 콤보박스는 `exports/terrain_generation`의 `.npz` 파일과 현재 열린 파일의 폴더를 최신순으로 보여준다. `Load Selected`는 선택한 파일을 현재 GPU 버퍼와 VAO에 다시 업로드하고, `Reload`는 현재 파일을 디스크에서 다시 읽는다. `Prev`와 `Next`는 목록의 이전/다음 파일을 즉시 로드하고, `Refresh`는 새로 export된 파일을 목록에 반영한다. `Use file palette`를 켜면 로드할 때 파일 metadata의 palette를 사용하고, `Reset camera on load`를 켜면 파일을 바꿀 때 카메라도 기본 위치로 돌아간다.

뷰어가 sphere terrain export를 읽었을 때는 우상단에 스피어 제너레이터와 같은 orientation gizmo를 그린다. 이 표시기는 북극 `N`, 경도 `0`, `+90`, `-90`, 현재 `view` 경도/위도를 보여주며, 카메라 회전 기준을 확인하는 용도다. 평면 terrain export에서는 표시하지 않는다.

GPU 뷰어는 레이어 편집 기능을 갖지 않는다. export 파일은 이미 bake된 메시 상태를 보는 결과물이고, 제너레이터는 레이어 스택을 만들고 수정하는 도구다. 이 둘을 분리하면 저장된 메시를 검사하는 화면과 레이어를 생성하는 화면이 섞이지 않는다.

GPU 뷰어 조작은 지형 생성기와 같은 카메라 조작을 따른다.

- 마우스 드래그: 카메라 회전
- 마우스 휠: 줌
- `C`: 팔레트 전환
- `HOME`: 카메라 초기화

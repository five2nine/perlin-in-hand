# Terrain ImGui Widget Implementation

## 목적

정적 지형 생성 유틸리티의 GPU 평면 제너레이터와 legacy CPU 제너레이터에 같은 위젯 인터페이스를 제공한다. 키보드 단축키는 유지하고, 같은 작업을 ImGui 패널에서도 수행할 수 있게 한다.

사용자가 선택할 수 있는 지형 종류와 속성의 의미는 [terrain_generation_options.md](terrain_generation_options.md)에 정리한다.

## 적용 대상

- `implementations/terrain_gpu_generator_plane/main_terrain_gpu_generator_plane.py`
- `implementations/terrain_legacy_generator_cpu/main_terrain_legacy_generator_cpu.py`
- `implementations/terrain_gpu_runtime_common/terrain_imgui.py`
- `implementations/terrain_legacy_common/terrain_imgui.py`

## 패널 구성

`TerrainImguiPanel`은 GPU 평면 제너레이터와 legacy CPU 제너레이터가 각각의 공통 모듈에서 사용하는 ImGui 오버레이 패널이다. legacy CPU 쪽은 GPU toolchain과 섞이지 않도록 `terrain_legacy_common`에 보관한 사본을 사용한다.

- 상태 표시: 백엔드 이름, FPS, GPU bake 또는 CPU compute 시간
- 전역 설정: 해상도 슬라이더, 팔레트 콤보, 지형 초기화, 카메라 초기화
- 출력: 현재 지형 메시를 `.npz` 파일로 저장하는 Export 버튼
- 레이어 추가: Random, Simple 1/2/3 Oct, Valley, Billow, Ridged, Warped 버튼
- 레이어 목록: enabled 체크박스, 선택 가능한 레이어 요약, 삭제 버튼
- 선택 레이어 편집: octaves, frequency, amplitude, persistence, lacunarity, valley power, warp strength, warp frequency

레이어 목록의 행은 체크박스, 고정 폭 선택 영역, 삭제 버튼으로 나눈다. 선택 영역이 남은 폭 전체를 차지하면 삭제 버튼의 클릭 영역이 밀려나므로, 목록 안에서는 선택 영역 폭을 명시적으로 제한한다.

레이어 토글과 삭제는 공용 위젯이 스택을 직접 수정하지 않고 앱 콜백을 호출한다.

- `set_layer_enabled(index, enabled)`
- `remove_layer(index)`
- `upload_terrain_stack()`

GPU 평면 제너레이터와 legacy CPU 지형 창은 `WindowConfig.aspect_ratio = None`으로 fixed viewport를 끈다. 기본 fixed viewport가 켜져 있으면 리사이즈 후 ModernGL-window의 내부 viewport와 ImGui의 전체 창 좌표가 달라져 버튼 히트 영역이 어긋난다. 카메라 투영은 각 앱의 `on_resize()`에서 현재 창 비율로 갱신한다.

`TerrainImguiPanel`은 렌더링 직전에 현재 `window.size`와 `window.buffer_size`를 다시 읽어 `io.display_size`와 `io.display_fb_scale`을 갱신한다. 패널 위치와 크기는 첫 실행 때만 기본값을 제안하고, 이후에는 ImGui의 이동/크기 변경/접기 상태를 유지한다. 창이 작아지면 새로 만드는 첫 패널의 기본 폭/높이와 레이어 목록 높이만 줄인다.

레이어 추가 버튼은 작은 프리셋 묶음으로 유지한다. `Random`은 레이어 종류, 옥타브, 나머지 속성을 랜덤으로 만든다. 랜덤 시작값은 과한 디테일을 피하기 위해 1~3 octave 범위를 쓴다. `1/2/3 Oct`는 Simple 레이어의 옥타브만 고정하고 나머지 속성은 랜덤으로 만든다. Valley, Billow, Ridged, Warped 버튼은 해당 레이어 종류를 학습용 프리셋처럼 빠르게 추가하고, 옥타브와 세부 속성은 랜덤으로 둔다. 세부 조정은 선택 레이어 편집 영역에서 하며, Octaves 슬라이더는 최대 6까지 열려 있다.

## 이벤트 처리

`moderngl_window.integrations.imgui.ModernglWindowRenderer`는 렌더링과 키 입력 전달에 사용한다. 마우스 입력은 `pyimgui 2.0` IO 속성에 맞춰 `TerrainImguiPanel`에서 직접 전달한다.

- 좌표는 `moderngl-window`의 pyglet 콜백이 전달하는 상단 원점 좌표를 viewport 기준으로 보정해 `io.mouse_pos`에 넣는다.
- 스크롤은 `io.mouse_wheel_horizontal`과 `io.mouse_wheel`에 누적한다.
- 버튼은 ModernGL-window의 `window.mouse.left/right/middle` 상수를 기준으로 ImGui 인덱스에 매핑한다.
- `io.want_capture_mouse`가 참이면 지형 카메라 드래그와 줌 처리를 막아 패널 조작과 카메라 조작이 겹치지 않게 한다.

## 의존성

`imgui>=2.0.0`을 사용한다. 현재 `pyimgui` 빌드는 Python 3.13 이상에서 실패하므로 프로젝트 실행 버전은 Python 3.12.x로 고정한다.

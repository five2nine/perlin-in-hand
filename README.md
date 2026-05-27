# 🏔️ Interactive 3D Perlin Noise Terrain (ModernGL)

ModernGL과 GLSL 셰이더를 활용하여 GPU 상에서 실시간으로 3D 펄린 노이즈 지형을 생성하고 시각화하는 인터랙티브 파이썬 애플리케이션입니다.

---

## 🌟 주요 특징 (Features)

* **GPU 가속 지형 생성**: GLSL 버텍스 셰이더 내부에서 Stefan Gustavson의 Classic 3D Noise 알고리즘을 수행하여 정교한 파도와 지형을 고속 렌더링합니다.
* **ImGui 지형 제어 패널**: 정적 지형 생성 유틸리티는 레이어 추가/삭제, 선택 레이어 편집, 해상도/팔레트 변경을 위젯 패널에서 조작합니다.
* **실시간 법선 벡터(Normal) 계산**: 유한차분법(Finite Difference)을 셰이더 내에서 활용하여 노이즈 높이에 따른 정확한 음영(Lighting)과 입체감을 표현합니다.
* **최적화된 프레임 제한**: VSync 비활성화 환경에서도 GPU 과부하(3500+ FPS)를 방지하기 위해 프로그램 자체에서 **60 FPS 프레임 캡(Capping)**을 지원합니다. (GPU 사용량을 50%+에서 1~2%로 절약)
* **카메라 극점 반전 예외 처리**: 창 최대화 혹은 빠른 화면 드래그 시 카메라 축이 180도 돌아가 뒤집히는 물리 특이점(lookAt Singularity) 문제를 방지하는 필터가 적용되어 있습니다.
* **모듈화된 셰이더 설계**: 관리 및 유지보수가 쉽도록 구현 방법별 폴더 아래에 실행 파일과 대응 셰이더를 함께 배치했습니다.
* **4가지 다이내믹 컬러 팔레트**: Viridis, Magma, Natural Terrain(자연 지형), Cyberpunk Neon 모드를 실시간으로 전환할 수 있습니다.

---

## 📂 프로젝트 구조 (Project Structure)

### 1. CPU 높이장 구현
* [main_perlin_2002_cpu.py](implementations/cpu_heightfield/main_perlin_2002_cpu.py): `perlin.Perlin`을 호출해 `(x, y, t)` 높이장을 계산하고 matplotlib 3D 표면으로 출력합니다.
* [main_opensimplex_2014_cpu.py](implementations/cpu_heightfield/main_opensimplex_2014_cpu.py): `opensimplex` 라이브러리로 `(x, y, t)` 높이장을 계산하고 matplotlib 3D 표면으로 출력합니다.

### 2. CPU 직접 Perlin 구현
* [main_perlin_my_cpu.py](implementations/cpu_manual_perlin/main_perlin_my_cpu.py): 2D Perlin의 gradient, dot product, fade 보간 절차를 직접 구현한 설명용 스크립트입니다.

### 3. GPU 높이장 구현
* [main_perlin_2002_gpu.py](implementations/gpu_heightfield/main_perlin_2002_gpu.py): GPU 셰이더에서 Perlin 높이장과 finite diff 법선을 계산합니다.
* [main_opensimplex_2014_gpu.py](implementations/gpu_heightfield/main_opensimplex_2014_gpu.py): GPU 셰이더에서 OpenSimplex2 높이장과 해석적 법선을 계산합니다.
* [shaders/perlin_2002.vert](implementations/gpu_heightfield/shaders/perlin_2002.vert): Perlin 높이장 버텍스 셰이더입니다.
* [shaders/opensimplex_2014.vert](implementations/gpu_heightfield/shaders/opensimplex_2014.vert): OpenSimplex2 높이장 버텍스 셰이더입니다.

### 4. 정적 지형 생성 유틸리티
* [main_gpu_terrain_generator.py](implementations/terrain_generation_gpu/main_gpu_terrain_generator.py): Marching Squares가 아닌 하이트필드 방식의 정적 `height = f(x, y)` 지형 생성기입니다. Random, Simple 1/2/3 Oct, Ridged, Billow, Valley, Warped 레이어를 더하고, GPU에서 한 번 구워 정적 VBO로 누적하며 ImGui/키보드 UI로 레이어를 추가·삭제합니다.
* [main_cpu_terrain_generator.py](implementations/terrain_generation_cpu/main_cpu_terrain_generator.py): GPU 버전과 같은 3D 창, 같은 ImGui/키보드 인터페이스, 같은 셰이더 출력물을 사용하되, 높이/노멀 VBO를 CPU에서 한 번 계산해 업로드하는 유틸리티입니다.
* [terrain_layers.py](implementations/terrain_generation_common/terrain_layers.py): GPU/CPU가 공유하는 지형 레이어 정의, 랜덤 레이어 생성, CPU 샘플러입니다.
* [terrain_imgui.py](implementations/terrain_generation_common/terrain_imgui.py): GPU/CPU 지형 생성기가 함께 사용하는 ImGui 위젯 패널입니다.
* [terrain_npz_loader.py](implementations/terrain_generation_common/terrain_npz_loader.py): Export된 `.npz` 지형 메시의 데이터와 형상을 세 뷰어가 같은 방식으로 읽기 위한 공용 로더입니다.
* [main_matplotlib_terrain_npz_viewer.py](implementations/terrain_npz_viewer_matplotlib/main_matplotlib_terrain_npz_viewer.py): Export된 `.npz` 지형 메시를 읽어 heightmap과 3D surface로 확인하는 Matplotlib 뷰어입니다.
* [main_pygame_terrain_npz_viewer.py](implementations/terrain_npz_viewer_pygame/main_pygame_terrain_npz_viewer.py): Export된 `.npz` 지형 메시를 CPU에서 색상화한 2D heightmap으로 빠르게 확인하는 pygame-ce 뷰어입니다.
* [main_gpu_terrain_npz_viewer.py](implementations/terrain_npz_viewer_gpu/main_gpu_terrain_npz_viewer.py): Export된 `.npz` 지형 메시를 제너레이터와 같은 ModernGL 렌더 셰이더로 보고, `Loaded Terrain` 패널에 파일 경로와 grid/triangle/height 같은 기본 사양을 표시하는 GPU 뷰어입니다.

### 5. 구면 지형 3D 노이즈 케이스
* [main_spherical_terrain_3d_noise.py](implementations/terrain_sphere_3d_noise/main_spherical_terrain_3d_noise.py): icosphere 방향 벡터를 3D gradient noise에 넣어 구면 terrain을 생성하고, 위도 밴드별 통계로 극점/적도 특성을 확인하는 ModernGL 케이스입니다.

### 6. GPU Marching Squares 구현
* [main_simplex_2d_gpu_marching_squares.py](implementations/gpu_marching_squares/main_simplex_2d_gpu_marching_squares.py): 2D simplex 밀도장 `d = func(x, y, t)`에서 Marching Squares로 등고선 선분을 추출하고, 공통 파라미터 기반 필드 모드(Single/fBm/Ridged/Billow)를 전환합니다.
* [shaders/marching_squares_tf.geom](implementations/gpu_marching_squares/shaders/marching_squares_tf.geom): transform feedback로 등고선 선분을 생성하는 geometry shader입니다.

### 7. GPU Marching Cubes 구현
* [main_opensimplex_2014_gpu_4d.py](implementations/gpu_marching_cubes/main_opensimplex_2014_gpu_4d.py): 4D simplex 밀도장 `d = func(x, y, z, t)`에서 Marching Cubes로 3D 등가면을 추출합니다.
* [marching_cubes_table.py](implementations/gpu_marching_cubes/marching_cubes_table.py): Marching Cubes 삼각화 테이블입니다.
* [shaders/marching_cubes_tf.geom](implementations/gpu_marching_cubes/shaders/marching_cubes_tf.geom): transform feedback로 등가면 삼각형을 생성하는 geometry shader입니다.

### 8. 기타 구현 자료
* [gpu_voxel_instancing_legacy](implementations/gpu_voxel_instancing_legacy): Marching Cubes 이전의 복셀 인스턴싱 방식 셰이더 보관 폴더입니다.
* [gpu_smoke_test/test_render.py](implementations/gpu_smoke_test/test_render.py): ModernGL 기본 렌더링 확인용 삼각형 테스트입니다.

### 9. 기술 문서
* [gui_architecture_qa.md](docs/gui_architecture_qa.md): 최적화(FPS, dt) 및 전문 GUI 연동 아키텍처 기술 Q&A 백서입니다.
* [spherical_terrain_3d_noise.md](docs/spherical_terrain_3d_noise.md): 구면 terrain을 3D 노이즈 샘플링으로 만드는 새 케이스의 의도, 실행법, 관찰 기준입니다.
* [spherical_terrain_study.md](docs/spherical_terrain_study.md): 평면 heightfield와 구면 terrain의 차이, 3D 방향 벡터 샘플링, icosphere, normal, 위도 밴드 통계를 설명하는 학습 노트입니다.
* [terrain_generation_options.md](docs/terrain_generation_options.md): 정적 지형 생성 유틸리티에서 선택할 수 있는 레이어 종류와 속성 옵션 설명입니다.
* [terrain_imgui_widget.md](docs/terrain_imgui_widget.md): 정적 지형 생성 유틸리티의 ImGui 위젯 패널 구현 기록입니다.
* [noise_complexity_comparison.md](docs/noise_complexity_comparison.md): 펄린 노이즈와 심플렉스 노이즈의 차원별 연산 절차 및 수학적 복잡도 분석 문서입니다.
* [terrain_synthesis_methods.md](docs/terrain_synthesis_methods.md): 단순 노이즈를 사실적인 산맥, 평야, 협곡 등으로 결합 및 가공하는 지형 합성 이론 가이드입니다.
* [field_extraction_qna.md](docs/field_extraction_qna.md): 높이장, 등가집합, threshold, slice, 셰이더 variant 관련 짧은 Q&A입니다.
* [noise_field_interpretation.md](docs/noise_field_interpretation.md): Simplex noise의 dot product, FEM 보간, score field 해석 메모입니다.

---

## 🛠️ 설치 및 실행 방법 (Installation & Usage)

### 요구사항
* Python 3.12.x
* `uv` 패키지 매니저 (추천) 또는 `pip`

### 실행 명령어

#### 펄린 노이즈 (2002) 실행:
* **CPU 버전**: `uv run .\implementations\cpu_heightfield\main_perlin_2002_cpu.py` (또는 `python .\implementations\cpu_heightfield\main_perlin_2002_cpu.py`)
* **CPU 직접 구현**: `uv run .\implementations\cpu_manual_perlin\main_perlin_my_cpu.py` (또는 `python .\implementations\cpu_manual_perlin\main_perlin_my_cpu.py`)
* **GPU 버전**: `uv run .\implementations\gpu_heightfield\main_perlin_2002_gpu.py` (또는 `python .\implementations\gpu_heightfield\main_perlin_2002_gpu.py`)

#### 오픈심플렉스 노이즈 (2014) 실행:
* **CPU 버전**: `uv run .\implementations\cpu_heightfield\main_opensimplex_2014_cpu.py` (또는 `python .\implementations\cpu_heightfield\main_opensimplex_2014_cpu.py`)
* **GPU 높이장 버전**: `uv run .\implementations\gpu_heightfield\main_opensimplex_2014_gpu.py` (또는 `python .\implementations\gpu_heightfield\main_opensimplex_2014_gpu.py`)

#### 정적 지형 생성 유틸리티 실행:
* **GPU 레이어 UI 버전**: `uv run .\implementations\terrain_generation_gpu\main_gpu_terrain_generator.py`
* **CPU 레이어 UI 버전**: `uv run .\implementations\terrain_generation_cpu\main_cpu_terrain_generator.py`
* **Matplotlib Export 뷰어**: `uv run .\implementations\terrain_npz_viewer_matplotlib\main_matplotlib_terrain_npz_viewer.py`
* **pygame-ce CPU Export 뷰어**: `uv run .\implementations\terrain_npz_viewer_pygame\main_pygame_terrain_npz_viewer.py`
* **GPU Export 뷰어**: `uv run .\implementations\terrain_npz_viewer_gpu\main_gpu_terrain_npz_viewer.py`
* **구면 3D 노이즈 케이스**: `uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py`
* **구면 3D 노이즈 통계 출력**: `uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py --analyze-only`

#### 등가집합 추출 실행:
* **GPU Marching Squares 버전**: `uv run .\implementations\gpu_marching_squares\main_simplex_2d_gpu_marching_squares.py` (또는 `python .\implementations\gpu_marching_squares\main_simplex_2d_gpu_marching_squares.py`)
* **GPU Marching Cubes 버전**: `uv run .\implementations\gpu_marching_cubes\main_opensimplex_2014_gpu_4d.py` (또는 `python .\implementations\gpu_marching_cubes\main_opensimplex_2014_gpu_4d.py`)

---

## 🎮 조작법 가이드 (Controls)

| 조작 키 / 마우스 | 기능 설명 |
| :--- | :--- |
| **마우스 좌클릭 드래그 (LMB)** | 카메라 각도 회전 (상하 궤도 고정 제한 적용) |
| **마우스 스크롤** | 카메라 줌인 / 줌아웃 (시야 거리 조절) |
| **SPACE** | 지형 파도 애니메이션 일시정지 / 재생 |
| **C** | 4가지 컬러 팔레트 순환 전환 (Viridis ➡️ Magma ➡️ Terrain ➡️ Cyberpunk) |
| **W** | 와이어프레임(Grid 라인) 모드 ↔️ 솔리드 면 모드 토글 |
| **R** | 카메라 줌 및 각도 기본값 초기화 |
| **방향키 위(▲) / 아래(▼)** | 격자 해상도 조절 [3D 지형: Resolution +/- 10, 최댓값 400] / 복셀 해상도 조절 [4D 치즈: Resolution +/- 8, 범위 8~256] |
| **방향키 좌(◀) / 우(▶)** | 4D W/시간축 슬라이스 좌표 조절 (Slice +/- 0.05) [4D 버전 전용] |
| **PAGE_UP / PAGE_DOWN** | 파도 진폭 높이 조절 [3D 지형: +/- 0.01] / 복셀 밀도 임계값 조절 [4D 치즈: +/- 0.05, 범위 -0.8~0.8] |

### 정적 지형 생성 유틸리티 조작

GPU/CPU 레이어 UI 버전은 같은 조작을 사용합니다.
창 좌측의 ImGui 패널에서도 같은 기능을 버튼, 체크박스, 콤보박스, 슬라이더로 조작할 수 있습니다.
ImGui `Export` 버튼은 현재 지형 메시를 `exports/terrain_generation/*.npz`로 저장합니다.
Matplotlib 뷰어는 경로를 생략하면 가장 최근 export 파일을 열고, 파일을 지정하면 해당 `.npz`를 엽니다.
pygame-ce CPU 뷰어는 같은 파일을 2D heightmap으로 표시합니다.
GPU Export 뷰어도 경로를 생략하면 가장 최근 CPU/GPU export 파일을 열고, 제너레이터와 같은 셰이더로 렌더링합니다.
GPU Export 뷰어의 `Loaded Terrain` 패널은 로딩된 파일과 기본 메시 사양을 표시합니다.

| 조작 키 / 마우스 | 기능 설명 |
| :--- | :--- |
| **1 / 2 / 3** | 1/2/3 옥타브 Simple 레이어를 랜덤 파라미터로 추가 |
| **A** | 랜덤 지형 레이어 추가 |
| **V / B / G / W** | Valley / Billow / Ridged / Warped 레이어 추가 |
| **TAB** | 선택 레이어 변경 |
| **E** | 선택 레이어 켜기 / 끄기 |
| **BACKSPACE / DELETE** | 선택 레이어 삭제 |
| **[ / ]** | 선택 레이어 진폭 감소 / 증가 |
| **PAGE_UP / PAGE_DOWN** | 선택 레이어 주파수 증가 / 감소 |
| **UP / DOWN** | 격자 해상도 증가 / 감소 |
| **C** | 컬러 팔레트 전환 |
| **R** | 지형 레이어 스택 초기화 |
| **HOME** | 카메라 초기화 |

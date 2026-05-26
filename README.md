# 🏔️ Interactive 3D Perlin Noise Terrain (ModernGL)

ModernGL과 GLSL 셰이더를 활용하여 GPU 상에서 실시간으로 3D 펄린 노이즈 지형을 생성하고 시각화하는 인터랙티브 파이썬 애플리케이션입니다.

---

## 🌟 주요 특징 (Features)

* **GPU 가속 지형 생성**: GLSL 버텍스 셰이더 내부에서 Stefan Gustavson의 Classic 3D Noise 알고리즘을 수행하여 정교한 파도와 지형을 고속 렌더링합니다.
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

### 4. GPU Marching Cubes 구현
* [main_opensimplex_2014_gpu_4d.py](implementations/gpu_marching_cubes/main_opensimplex_2014_gpu_4d.py): 4D simplex 밀도장 `d = func(x, y, z, t)`에서 Marching Cubes로 3D 등가면을 추출합니다.
* [marching_cubes_table.py](implementations/gpu_marching_cubes/marching_cubes_table.py): Marching Cubes 삼각화 테이블입니다.
* [shaders/marching_cubes_tf.geom](implementations/gpu_marching_cubes/shaders/marching_cubes_tf.geom): transform feedback로 등가면 삼각형을 생성하는 geometry shader입니다.

### 5. 기타 구현 자료
* [gpu_voxel_instancing_legacy](implementations/gpu_voxel_instancing_legacy): Marching Cubes 이전의 복셀 인스턴싱 방식 셰이더 보관 폴더입니다.
* [gpu_smoke_test/test_render.py](implementations/gpu_smoke_test/test_render.py): ModernGL 기본 렌더링 확인용 삼각형 테스트입니다.

### 6. 기술 문서
* [gui_architecture_qa.md](docs/gui_architecture_qa.md): 최적화(FPS, dt) 및 전문 GUI 연동 아키텍처 기술 Q&A 백서입니다.
* [noise_complexity_comparison.md](docs/noise_complexity_comparison.md): 펄린 노이즈와 심플렉스 노이즈의 차원별 연산 절차 및 수학적 복잡도 분석 문서입니다.
* [terrain_synthesis_methods.md](docs/terrain_synthesis_methods.md): 단순 노이즈를 사실적인 산맥, 평야, 협곡 등으로 결합 및 가공하는 지형 합성 이론 가이드입니다.

---

## 🛠️ 설치 및 실행 방법 (Installation & Usage)

### 요구사항
* Python 3.13 이상
* `uv` 패키지 매니저 (추천) 또는 `pip`

### 실행 명령어

#### 펄린 노이즈 (2002) 실행:
* **CPU 버전**: `uv run .\implementations\cpu_heightfield\main_perlin_2002_cpu.py` (또는 `python .\implementations\cpu_heightfield\main_perlin_2002_cpu.py`)
* **CPU 직접 구현**: `uv run .\implementations\cpu_manual_perlin\main_perlin_my_cpu.py` (또는 `python .\implementations\cpu_manual_perlin\main_perlin_my_cpu.py`)
* **GPU 버전**: `uv run .\implementations\gpu_heightfield\main_perlin_2002_gpu.py` (또는 `python .\implementations\gpu_heightfield\main_perlin_2002_gpu.py`)

#### 오픈심플렉스 노이즈 (2014) 실행:
* **CPU 버전**: `uv run .\implementations\cpu_heightfield\main_opensimplex_2014_cpu.py` (또는 `python .\implementations\cpu_heightfield\main_opensimplex_2014_cpu.py`)
* **GPU 높이장 버전**: `uv run .\implementations\gpu_heightfield\main_opensimplex_2014_gpu.py` (또는 `python .\implementations\gpu_heightfield\main_opensimplex_2014_gpu.py`)
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
| **방향키 좌(◀) / 우(▶)** | 4D 슬라이스 좌표(Slice) 조절 (Slice +/- 0.05) [4D 버전 전용] |
| **PAGE_UP / PAGE_DOWN** | 파도 진폭 높이 조절 [3D 지형: +/- 0.01] / 복셀 밀도 임계값 조절 [4D 치즈: +/- 0.05, 범위 -0.8~0.8] |

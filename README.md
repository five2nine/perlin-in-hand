# 🏔️ Interactive 3D Perlin Noise Terrain (ModernGL)

ModernGL과 GLSL 셰이더를 활용하여 GPU 상에서 실시간으로 3D 펄린 노이즈 지형을 생성하고 시각화하는 인터랙티브 파이썬 애플리케이션입니다.

---

## 🌟 주요 특징 (Features)

* **GPU 가속 지형 생성**: GLSL 버텍스 셰이더 내부에서 Stefan Gustavson의 Classic 3D Noise 알고리즘을 수행하여 정교한 파도와 지형을 고속 렌더링합니다.
* **실시간 법선 벡터(Normal) 계산**: 유한차분법(Finite Difference)을 셰이더 내에서 활용하여 노이즈 높이에 따른 정확한 음영(Lighting)과 입체감을 표현합니다.
* **최적화된 프레임 제한**: VSync 비활성화 환경에서도 GPU 과부하(3500+ FPS)를 방지하기 위해 프로그램 자체에서 **60 FPS 프레임 캡(Capping)**을 지원합니다. (GPU 사용량을 50%+에서 1~2%로 절약)
* **카메라 극점 반전 예외 처리**: 창 최대화 혹은 빠른 화면 드래그 시 카메라 축이 180도 돌아가 뒤집히는 물리 특이점(lookAt Singularity) 문제를 방지하는 필터가 적용되어 있습니다.
* **모듈화된 셰이더 설계**: 관리 및 유지보수가 쉽도록 버텍스/프레임 셰이더 코드를 각각 `shaders/` 폴더 산하의 `perlin_2002.vert`와 `perlin_2002.frag` 파일로 분리했습니다.
* **4가지 다이내믹 컬러 팔레트**: Viridis, Magma, Natural Terrain(자연 지형), Cyberpunk Neon 모드를 실시간으로 전환할 수 있습니다.

---

## 📂 프로젝트 구조 (Project Structure)

### 1. 2002년 개선형 펄린 노이즈 (Perlin Noise 2002)
* [main_perlin_2002_cpu.py](file:///g:/dev/Playground/perlin-in-hand/main_perlin_2002_cpu.py): **CPU 연산** 기반으로 펄린 노이즈를 계산하여 matplotlib 3D 애니메이션으로 출력하는 파이썬 스크립트입니다.
* [main_perlin_2002_gpu.py](file:///g:/dev/Playground/perlin-in-hand/main_perlin_2002_gpu.py): **GPU 연산** 기반으로 펄린 노이즈 및 법선 벡터를 셰이더에서 계산하고 ModernGL로 실시간 렌더링하는 파이썬 엔트리포인트입니다.
* [perlin_2002.vert](file:///g:/dev/Playground/perlin-in-hand/shaders/perlin_2002.vert): 5차 다항식을 활용해 연속된 2차 미분(C2 연속성)을 연산하고 법선 벡터를 셰이더 내에서 연산하는 버텍스 셰이더입니다.
* [perlin_2002.frag](file:///g:/dev/Playground/perlin-in-hand/shaders/perlin_2002.frag): 펄린 노이즈 높이에 따른 조명 및 컬러 매핑 프래그먼트 셰이더입니다.

### 2. 2014년 오픈심플렉스 노이즈 (OpenSimplex Noise 2014)
* [main_opensimplex_2014_cpu.py](file:///g:/dev/Playground/perlin-in-hand/main_opensimplex_2014_cpu.py): **CPU 연산** 기반으로 오픈심플렉스 노이즈를 계산하여 matplotlib 3D 애니메이션으로 출력하는 파이썬 스크립트입니다.
* [main_opensimplex_2014_gpu.py](file:///g:/dev/Playground/perlin-in-hand/main_opensimplex_2014_gpu.py): **GPU 연산** 기반으로 3D 오픈심플렉스 노이즈를 계산하고 ModernGL로 실시간 렌더링하는 파이썬 엔트리포인트입니다.
* [main_opensimplex_2014_gpu_4d.py](file:///g:/dev/Playground/perlin-in-hand/main_opensimplex_2014_gpu_4d.py): **GPU 연산** 기반으로 4D 심플렉스 노이즈를 연산하여 3D 볼륨의 복셀 스위스 치즈(Voxel Swiss Cheese) 블록을 실시간 렌더링하고 시각화하는 파이썬 엔트리포인트입니다.
* [opensimplex_2014.vert](file:///g:/dev/Playground/perlin-in-hand/shaders/opensimplex_2014.vert): 3차원 공간 상에서 4-Point BCC 격자 탐색(OpenSimplex2S)을 통해 축 정렬 격자 줄무늬 왜곡을 해소하고, **해석적 도함수(Analytical Derivative)**를 활용해 0의 오차로 즉각적인 법선 벡터를 추출해 내는 버텍스 셰이더입니다.
* [opensimplex_2014_4d.vert](file:///g:/dev/Playground/perlin-in-hand/shaders/opensimplex_2014_4d.vert): 4차원 공간(3D 복셀 공간 + 시간) 상에서 Stefan Gustavson의 4D Simplex Noise를 연산하고, 밀도 임계값을 통해 내부 구멍을 깎아내는 인스턴싱 복셀용 버텍스 셰이더입니다.
* [opensimplex_2014.frag](file:///g:/dev/Playground/perlin-in-hand/shaders/opensimplex_2014.frag): 3D 오픈심플렉스 지형 전용 프래그먼트 셰이더입니다.
* [opensimplex_2014_4d.frag](file:///g:/dev/Playground/perlin-in-hand/shaders/opensimplex_2014_4d.frag): 4D 심플렉스 복셀 치즈 전용 프래그먼트 셰이더입니다.

### 3. 기술 문서
* [gui_architecture_qa.md](file:///g:/dev/Playground/perlin-in-hand/docs/gui_architecture_qa.md): 최적화(FPS, dt) 및 전문 GUI 연동 아키텍처 기술 Q&A 백서입니다.
* [noise_complexity_comparison.md](file:///g:/dev/Playground/perlin-in-hand/docs/noise_complexity_comparison.md): 펄린 노이즈와 심플렉스 노이즈의 차원별 연산 절차 및 수학적 복잡도 분석 문서입니다.
* [terrain_synthesis_methods.md](file:///g:/dev/Playground/perlin-in-hand/docs/terrain_synthesis_methods.md): 단순 노이즈를 사실적인 산맥, 평야, 협곡 등으로 결합 및 가공하는 지형 합성 이론 가이드입니다.

---

## 🛠️ 설치 및 실행 방법 (Installation & Usage)

### 요구사항
* Python 3.13 이상
* `uv` 패키지 매니저 (추천) 또는 `pip`

### 실행 명령어

#### 펄린 노이즈 (2002) 실행:
* **CPU 버전**: `uv run .\main_perlin_2002_cpu.py` (또는 `python .\main_perlin_2002_cpu.py`)
* **GPU 버전**: `uv run .\main_perlin_2002_gpu.py` (또는 `python .\main_perlin_2002_gpu.py`)

#### 오픈심플렉스 노이즈 (2014) 실행:
* **CPU 버전**: `uv run .\main_opensimplex_2014_cpu.py` (또는 `python .\main_opensimplex_2014_cpu.py`)
* **GPU 3D 버전**: `uv run .\main_opensimplex_2014_gpu.py` (또는 `python .\main_opensimplex_2014_gpu.py`)
* **GPU 4D 버전 (복셀 치즈)**: `uv run .\main_opensimplex_2014_gpu_4d.py` (또는 `python .\main_opensimplex_2014_gpu_4d.py`)

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

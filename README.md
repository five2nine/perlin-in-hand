# terrain-noise-workbench-2026

`terrain-noise-workbench-2026`은 Perlin, OpenSimplex, fBm 계열 노이즈를 CPU와 GPU에서 비교하며 지형처럼 다뤄 보는 Python 실험 저장소다. 단일 렌더링 앱이 아니라 heightfield, 정적 terrain export, 구면 terrain, Marching Squares/Cubes, Transform Feedback를 한 폴더 안에서 확인하는 작업대에 가깝다.

이 저장소의 전신 이름은 `perlin-in-hand`였지만, 현재 내용은 Perlin 하나보다 넓다. 그래서 프로젝트 이름을 `terrain-noise-workbench-2026`으로 정리한다.

## 현재 정리 상태

| 항목 | 기준 |
| --- | --- |
| 프로젝트 이름 | `terrain-noise-workbench-2026` |
| 기본 브랜치 | `main` |
| 기본 Python | `3.14.6` |
| 패키지 관리 | `uv` |
| 기본 실행 범위 | `imgui`가 필요 없는 CPU/GPU 실험 |
| 별도 확인 실행 범위 | ImGui 기반 terrain 생성기/뷰어 |

Python 최신화는 기본 환경을 `3.14.6`으로 맞추는 방식으로 적용한다. 다만 이번 정리 중 깨끗한 `uv sync`에서 `imgui==2.0.0` 빌드가 Python 3.13/3.14 계열에서 실패했다. 기존에 준비된 Python 3.13 환경에서 이미 동작하던 경우는 별도이며, 그 사실을 부정하지 않는다. 그래서 ImGui 기반 실행 파일은 기본 의존성에서 제외하고 `imgui-legacy` 선택 의존성으로 분리했다.

정리 시점인 2026-07-09 기준 Python.org의 stable source release 목록에서 3.14 계열 최신 안정판은 `3.14.6`이다. `imgui` 호환성 문제는 이번 clean sync 실패와 PyPI의 `imgui` 배포 상태, pyimgui의 Python 3.13 빌드 오류 이슈를 기준으로 기록했다.

## 폴더 구조

| 경로 | 내용 |
| --- | --- |
| `implementations/heightfield_cpu` | 직접 구현 Perlin, `perlin`, `opensimplex`를 matplotlib 표면으로 확인하는 CPU heightfield 실험 |
| `implementations/heightfield_gpu` | ModernGL 셰이더에서 Perlin/OpenSimplex heightfield와 법선을 계산하는 GPU 실험 |
| `implementations/terrain_gpu_runtime_common` | GPU terrain 생성기와 뷰어가 공유하는 레이어, export/import, ImGui 패널 코드 |
| `implementations/terrain_gpu_generator_plane` | 평면 heightfield 지형을 GPU에서 구워 `.npz`로 저장하는 생성기 |
| `implementations/terrain_gpu_generator_sphere` | icosphere 방향 벡터를 3D 노이즈에 넣어 구면 지형을 만드는 생성기 |
| `implementations/terrain_gpu_viewer` | export된 terrain `.npz`를 ModernGL로 다시 여는 뷰어 |
| `implementations/terrain_legacy_*` | CPU 생성기와 matplotlib/pygame 기반 확인 도구 |
| `implementations/gpu_marching_squares` | 2D 밀도장에서 등고선 선분을 추출하는 Transform Feedback 실험 |
| `implementations/gpu_marching_cubes` | 3D/4D 밀도장에서 등가면 삼각형을 추출하는 Transform Feedback 실험 |
| `docs` | 카메라, transform feedback, spherical terrain, ImGui 패널, 노이즈 비교 문서 |

## 설치

기본 환경은 최신 Python 라인인 3.14 계열을 사용한다.

```powershell
uv sync --python 3.14
```

정확히 이 저장소가 고정한 버전을 쓰려면 다음처럼 실행한다.

```powershell
uv sync --python 3.14.6
```

기본 환경에는 `imgui`가 설치되지 않는다. 따라서 ImGui 패널을 직접 import하는 실행 파일은 기본 환경에서 실행 대상이 아니다.

## ImGui 별도 확인 범위

ImGui 기반 파일은 아래처럼 `import imgui` 또는 `moderngl_window.integrations.imgui`에 의존한다.

- `implementations/terrain_gpu_generator_plane/main_terrain_gpu_generator_plane.py`
- `implementations/terrain_gpu_generator_sphere/main_terrain_gpu_generator_sphere.py`
- `implementations/terrain_gpu_viewer/main_terrain_gpu_viewer.py`
- `implementations/terrain_legacy_generator_cpu/main_terrain_legacy_generator_cpu.py`
- `implementations/terrain_gpu_runtime_common/terrain_imgui.py`
- `implementations/terrain_legacy_common/terrain_imgui.py`

`imgui-legacy` extra는 별도 확인용으로 남겨 둔다.

```powershell
uv sync --extra imgui-legacy
```

이번 정리 중에는 깨끗한 Python 3.13/3.14 환경에서 `imgui==2.0.0` C 확장 빌드가 실패했다. 반대로 기존 Python 3.13 가상환경에 이미 `imgui`가 설치되어 있고 실행까지 됐다면 그 환경은 그대로 유효한 실험 기록으로 봐야 한다. 이 저장소의 기본 정책은 최신 Python 환경을 우선 유지하고, ImGui 실행군은 별도 검증 대상으로 분리해 보관하는 것이다.

참고 링크:

- [Python source releases](https://www.python.org/downloads/source/)
- [imgui on PyPI](https://pypi.org/project/imgui/)
- [pyimgui Python 3.13 build error](https://github.com/pyimgui/pyimgui/issues/383)

## 실행 예

기본 환경에서 우선 확인할 수 있는 실행군은 ImGui를 직접 쓰지 않는 스크립트다.

```powershell
uv run .\implementations\heightfield_cpu\main_perlin_my_cpu.py
uv run .\implementations\heightfield_cpu\main_perlin_2002_cpu.py
uv run .\implementations\heightfield_cpu\main_opensimplex_2014_cpu.py
uv run .\implementations\heightfield_gpu\main_perlin_2002_gpu.py
uv run .\implementations\heightfield_gpu\main_opensimplex_2014_gpu.py
uv run .\implementations\gpu_marching_squares\main_simplex_2d_gpu_marching_squares.py
uv run .\implementations\gpu_marching_cubes\main_opensimplex_2014_gpu_4d.py
```

GPU 실행 파일은 ModernGL이 OpenGL 컨텍스트를 만들 수 있는 로컬 그래픽 환경을 필요로 한다.

## 산출물과 로컬 전용 폴더

실행 결과는 저장소에 기본 포함하지 않는다.

| 경로 | 의미 |
| --- | --- |
| `.venv/` | `uv sync`가 만드는 로컬 가상환경 |
| `outputs/` | CPU/GPU 실험에서 생성되는 이미지, 영상, 기타 출력 |
| `exports/` | terrain 생성기가 저장하는 `.npz` 메시 export |
| `__pycache__/` | Python 캐시 |

export `.npz` 메타데이터의 format 이름도 `terrain-noise-workbench-2026 terrain npz`로 정리했다.

## 문서

- `docs/spherical_terrain_3d_noise.md`: 구면 terrain을 3D 방향 벡터 샘플링으로 만드는 실험 기록
- `docs/spherical_terrain_study.md`: 평면 heightfield와 구면 terrain의 차이 정리
- `docs/transform_feedback_pipeline.md`: Transform Feedback 파이프라인과 terrain bake, Marching Squares/Cubes 비교
- `docs/terrain_generation_options.md`: terrain 레이어 종류와 속성 설명
- `docs/terrain_imgui_widget.md`: ImGui 패널 구현과 현재 clean sync 기준 Python 호환성 제약
- `docs/noise_complexity_comparison.md`: Perlin/Simplex 노이즈의 연산 절차 비교
- `docs/terrain_synthesis_methods.md`: 산맥, 평야, 협곡 등으로 노이즈를 가공하는 합성 메모

## 검증 기준

기본 환경 검증은 다음 순서로 본다.

```powershell
uv lock --check
uv sync --python 3.14.6
uv run python -m compileall implementations
uv run python -c "import numpy, matplotlib, moderngl, glcontext, imageio, opensimplex, pygame; print('default dependencies ok')"
```

ImGui 실행군은 이번 clean sync에서 `imgui` 빌드 실패가 확인됐으므로 최신 Python 기본 검증 대상에서 제외한다. 기존에 준비된 Python 3.13 환경이 남아 있다면 그 환경에서 별도 실행 검증을 하는 편이 맞다.

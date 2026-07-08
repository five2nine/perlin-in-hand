# Python 3.12.12 고정과 ImGui 의존성

## 결론

이 저장소는 `Python 3.12.12`를 기준 실행 환경으로 둔다. `Python 3.13` 이상으로 올리지 않는다.

이유는 Python 자체가 목적이 아니라 `imgui==2.0.0` 때문이다. 이 프로젝트의 terrain 생성기와 뷰어는 ImGui 패널을 직접 사용한다. 따라서 `imgui`를 빼고 최신 Python만 통과시키는 방식은 이 저장소의 전체 기능 검증으로 보지 않는다.

## clean install 테스트

테스트 일자: 2026-07-09

| Python | `imgui==2.0.0` 설치 | import | 판단 |
| --- | --- | --- | --- |
| `3.12.12` | 성공 | 성공 | 기준 버전으로 사용 |
| `3.13.12` | 실패 | 불가 | 올리지 않음 |
| `3.14.6` | 실패 | 불가 | 올리지 않음 |

`Python 3.12.12`에서는 `imgui==2.0.0`이 설치되고 `import imgui`까지 통과했다.

`Python 3.13.12`와 `Python 3.14.6`에서는 `imgui==2.0.0` 빌드가 실패했다. 실패 로그에는 `_PyInterpreterState_GetConfig`, `_PyList_Extend`, `_PyLong_AsByteArray`, `_PyGen_SetStopIterationValue` 관련 C API 오류가 나타났다.

## 정책

`pyproject.toml`은 다음 범위를 사용한다.

```toml
requires-python = ">=3.12,<3.13"
```

`.python-version`은 다음 버전을 사용한다.

```text
3.12.12
```

`imgui>=2.0.0`은 optional dependency가 아니라 기본 dependency다. 이 프로젝트의 주요 실행 파일이 ImGui 패널을 쓰기 때문이다.

## 검증 명령

```powershell
uv sync --python 3.12.12
uv run python -m compileall implementations
uv run python -c "import numpy, matplotlib, moderngl, glcontext, imageio, opensimplex, pygame, imgui; print('dependencies ok')"
```

## 참고 링크

- [imgui on PyPI](https://pypi.org/project/imgui/)
- [pyimgui Python 3.13 build error](https://github.com/pyimgui/pyimgui/issues/383)

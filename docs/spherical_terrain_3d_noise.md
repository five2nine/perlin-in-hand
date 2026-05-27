# 구면 Terrain 3D 노이즈 샘플링 케이스

## 목적

구면 terrain에서 위도/경도 UV 샘플링을 쓰지 않고, 구면 위의 방향 벡터를 3D noise field에 직접 넣었을 때 적도와 극점의 특성이 어떻게 나타나는지 확인한다.

개념을 공부하기 위한 설명과 작업 중 나온 질문과 답변은 [spherical_terrain_study.md](spherical_terrain_study.md)에 정리한다. 이 문서는 실행법과 관찰 기준을 중심으로 둔다.

GPU에서 terrain 샘플 생성을 처리하기 위한 선택지, 특히 tessellation shader와 compute shader의 차이도 같은 학습 문서의 Q&A에 기록한다. 현재 구현은 compute shader 경로를 사용한다.

핵심 샘플링 식은 다음과 같다.

```text
direction = normalize(vertex_position)
height = sum(layer_noise3D(direction, layer_params))
surface_position = direction * (radius + height)
```

이 방식은 북극/남극을 특별한 좌표점으로 만들지 않는다. 극점은 위도/경도 좌표계의 특이점이고, 3D 방향 벡터 샘플링에서는 모든 표면점이 같은 3D noise field의 단면을 읽는다.

## 실행

```powershell
uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py
```

창 없이 기본 통계만 확인할 때는 다음 명령을 사용한다.

```powershell
uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py --analyze-only
```

파라미터를 지정할 수 있다.

```powershell
uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py --subdivisions 6 --frequency 3.2 --amplitude 0.12 --octaves 5 --seed 41
```

정지 상태의 GPU 사용량을 낮추기 위해 기본 렌더링 cap은 입력 중 60FPS, idle 상태 12FPS다. 필요하면 다음처럼 조절한다.

```powershell
uv run .\implementations\terrain_sphere_3d_noise\main_spherical_terrain_3d_noise.py --active-fps 60 --idle-fps 8
```

## 구현 구조

- 베이스 메쉬는 위도/경도 격자가 아니라 `icosphere`다.
- `subdivisions`가 높아질수록 삼각형 수와 vertex 수가 증가한다.
- 기본값은 `subdivisions = 6`이며, UI와 명령행에서는 최대 8까지 올릴 수 있다.
- 화면에 변화가 없어도 ModernGL 창은 렌더 루프를 돈다. 현재 케이스는 입력이 없으면 idle FPS cap을 낮춰 고밀도 구면 mesh의 정지 상태 GPU 사용량을 줄인다.
- compute shader가 정이십면체의 20개 base triangle을 `2^subdivisions` 격자로 직접 펼친다.
- compute shader가 subdivision, height, displaced position, normal을 한 번에 terrain vertex buffer에 쓴다.
- 현재 GPU subdivision은 index buffer를 만들지 않고 non-indexed triangle list를 생성한다. 따라서 논리적 공유 vertex 수보다 실제 draw vertex 수가 크다.
- 평면 terrain generator와 같은 레이어 스택 개념을 사용한다. `Simple`, `fBm`, `Ridged`, `Billow`, `Valley`, `Warped` 레이어를 enabled 상태에 따라 누적한다.
- UI에서 레이어를 추가, 삭제, enable/disable하거나 frequency, amplitude, octave, persistence, lacunarity, valley_power, warp_strength, warp_frequency를 바꾸면 같은 buffer 크기에서 compute shader만 다시 dispatch한다.
- 선택 레이어의 octaves는 최대 6까지 조정할 수 있다. Random 프리셋은 기본 관찰이 너무 촘촘해지지 않도록 1~3 octave 범위에서 시작한다.
- UI에서 subdivisions를 바꾸면 draw vertex 수가 바뀌므로 terrain vertex buffer를 다시 잡고 compute shader를 dispatch한다.
- 정확한 height 범위와 위도 밴드 통계는 GPU buffer readback이 필요하므로 `Read GPU Stats` 버튼으로 요청할 때만 읽는다.
- 각 vertex의 정규화 방향 벡터를 3D gradient noise 입력으로 사용한다.
- 각 레이어 내부에서 fBm은 여러 octave의 3D noise를 더해 만든다.
- 높이 변위는 radial displacement로 적용한다.
- terrain vertex는 seed가 아니라 노이즈 샘플 위치다. 현재 노이즈의 베이스 그리드는 terrain mesh가 아니라 3D XYZ 노이즈 공간의 정수 cubic lattice다.
- random gradient는 저장된 배열이 아니라 정수 lattice 좌표와 seed를 hash해서 즉석 생성한다.
- 렌더링은 기존 지형 렌더 셰이더 `terrain_heightfield.vert/frag`를 재사용한다.

## 패널 정보

ModernGL 창의 ImGui 패널은 다음 항목을 표시한다.

- subdivisions
- 레이어 추가 버튼: Random, 1 Oct, 2 Oct, 3 Oct, Valley, Billow, Ridged, Warped
- 레이어 목록: 선택, enabled, 삭제
- 선택 레이어 속성: frequency, amplitude, octaves(1~6), persistence, lacunarity, valley_power, warp_strength, warp_frequency
- logical vertex 수
- draw vertex 수
- triangle 수
- height 범위
- 위도 밴드별 count, mean, standard deviation

오른쪽 상단의 작은 표시기는 현재 카메라 회전 기준을 보여준다.

- 작은 원형 구: 현재 구면 좌표계의 축 방향을 2D로 투영한 표시기
- `N`: 북극, 즉 `+Y` 방향
- `0`: 경도 0도, 즉 적도상의 `+X` 방향
- `+90`: 경도 90도, 즉 적도상의 `+Z` 방향
- `-90`: 경도 -90도, 즉 적도상의 `-Z` 방향
- `view`: 현재 카메라가 바라보는 구면 기준 경도/위도

표시기는 카메라 회전에 따라 함께 회전한다. 앞쪽 반구의 경선과 마커는 밝게, 뒤쪽 반구의 선과 마커는 흐리게 표시한다.

위도 밴드는 다음 다섯 구간이다.

- south polar: -90도 .. -60도
- south mid: -60도 .. -30도
- equatorial: -30도 .. 30도
- north mid: 30도 .. 60도
- north polar: 60도 .. 90도

## 관찰 기준

3D 방향 벡터 샘플링은 UV 극점 압축을 만들지 않는다. 따라서 적도와 극점의 차이는 좌표 매핑 문제라기보다 다음 요인에서 나온다.

- 유한한 vertex 수 때문에 밴드별 표본 수가 다르다.
- 한 seed의 noise 결과는 무작위 실현 하나이므로 밴드별 mean과 standard deviation이 완전히 같지는 않다.
- 현재 3D noise는 내부적으로 정수 cubic lattice hash를 쓰므로 아주 낮은 frequency나 특정 seed에서 약한 축 방향 artifact가 보일 수 있다.
- icosphere도 완전 균일한 면적 분포는 아니므로 밴드 통계에는 작은 샘플링 차이가 남는다.

기본값에서 `--analyze-only` 출력은 위도 밴드별 표준편차가 큰 차이 없이 비슷한 범위에 놓이는지 확인하기 위한 첫 기준이다. 극점 쪽에서 일관된 압축이나 늘어남이 보이는지 확인하려면 seed와 frequency를 바꿔 여러 번 비교한다.

## 조작

- 마우스 드래그: 카메라 회전
- 마우스 휠: 줌
- `C`: 팔레트 전환
- `W`: 와이어프레임 전환
- `HOME`: 카메라 초기화

패널 위에서 마우스를 조작하면 카메라 회전/줌과 충돌하지 않는다.

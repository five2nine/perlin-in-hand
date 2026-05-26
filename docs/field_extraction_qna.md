# Field Extraction Q&A Notes

## Height Field vs Scalar Field

Q. `z = func(x, y, t)`와 `d = func(x, y, z, t)`는 같은가?

A. 다르다. 높이장은 모든 `(x, y)`에 높이 하나를 직접 그린다. 스칼라장은 `d == threshold`인 등가집합만 추출해 그린다.

## Displacement

Q. Marching Cubes는 `(u, v, w) = func(x, y, z)`를 더해 `(x+u, y+v, z+w)`를 그리는가?

A. 아니다. 각 voxel edge에서 밀도가 threshold를 지나는 위치를 보간해 삼각형 정점을 만든다.

## Extractor

Q. 2D와 3D를 같은 추출기로 처리할 수 있는가?

A. 추출기는 분리한다. 2D는 Marching Squares로 4개 꼭짓점에서 선분을 만들고, 3D는 Marching Cubes로 8개 꼭짓점에서 삼각형을 만든다.

## Shader Variant

Q. `func3(vec3(x, y, 0))`로 2D를 통합해도 되는가?

A. 셰이더 기준으로 비효율적이다. 2D 샘플에도 3D noise 비용을 낸다. 공통 런타임 분기보다 2D, 2D+t, 3D, 3D+w variant를 따로 컴파일하는 쪽이 맞다.

## Frequency

Q. `frequency`는 파인 격자를 만드는가?

A. 아니다. `resolution`은 샘플링 격자이고, `frequency`는 noise 입력 좌표 스케일이다. 저장되는 파인 격자가 늘어나는 구조가 아니다.

## Threshold

Q. 2D에는 threshold가 없고 3D에는 threshold가 있는 이유는 무엇인가?

A. 기존 2D 구현은 높이장이므로 threshold가 없었다. Marching Squares와 Marching Cubes는 스칼라장의 `d == threshold`를 추출하므로 threshold가 필요하다.

## Slice

Q. 3D의 `slice`는 threshold와 같은가?

A. 아니다. threshold는 등밀도 값을 고른다. slice는 extra noise coordinate를 고정한다. 현재 Marching Cubes 코드의 `slice`는 4D noise의 `w` 좌표이며, 코드상 `w = slice + time`이다.

## `snoise`

Q. `snoise`는 무엇인가?

A. simplex noise의 관용적 함수명이다. 시그니처가 중요하다. `snoise(vec2)`는 2D noise이고, `snoise(vec3)`는 `func(x, y, t)`나 `func(x, y, z)`에 대응한다.

## Animation

Q. Marching Squares가 xy 평면에서 평행 이동처럼 보인 이유는 무엇인가?

A. `noise2(x + a*t, y + b*t)`로 입력 좌표를 밀었기 때문이다. `func(x, y, t)`에는 `snoise(vec3(x, y, t))` 형태가 맞다.

## Line Width

Q. pyglet HUD에서 `GL_INVALID_VALUE`가 난 이유는 무엇인가?

A. 일부 OpenGL core profile에서 `line_width > 1` 설정이 invalid value를 남겼고, 이후 pyglet 텍스트 렌더링이 그 에러를 감지했다. 기본 line width를 쓰거나 두꺼운 선은 geometry로 만든다.

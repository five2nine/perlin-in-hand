# Noise Field Interpretation Notes

## Simplex 계산식

Simplex noise의 스칼라 값은 주변 simplex 꼭짓점의 기여를 감쇠 가중합한 값이다.

```text
d(p) = sum_i w_i(p) * dot(g_i, p - v_i)
```

- `p`: 샘플 위치
- `v_i`: 주변 simplex 꼭짓점
- `g_i`: 꼭짓점에 고정된 pseudo-random gradient
- `w_i(p)`: 꼭짓점 영향력을 줄이는 방사형 감쇠 가중치
- `d(p)`: 최종 스칼라 필드 값

## Dot Product와 적분 해석

꼭짓점 하나의 gradient `g_i`를 상수 벡터장으로 보면, 꼭짓점 `v_i`에서 샘플 위치 `p`까지의 선적분은 dot product와 같다.

```text
integral g_i dot dx = g_i dot (p - v_i)
```

따라서 `dot(g_i, p - v_i)`는 "기울기 벡터를 변위에 대해 적분한 값"처럼 해석할 수 있다.

다만 전체 Simplex noise는 단일 전역 적분값이 아니다. 여러 꼭짓점의 국소 선형 기여를 `w_i(p)`로 감쇠해 섞은 스칼라 필드다.

## FEM 관점

FEM과의 대응은 다음처럼 볼 수 있다.

```text
Simplex: d(p) = sum_i w_i(p) * local_i(p)
FEM    : u(p) = sum_i N_i(p) * value_i
```

여기서 `w_i(p)`는 shape function 또는 basis function과 비슷한 역할을 한다. `dot(g_i, p - v_i)`는 노드 주변의 1차 국소 근사값처럼 볼 수 있다.

차이는 분명하다.

- FEM의 노드 값과 기울기는 물리 방정식, 경계조건, 에너지 최소화에서 나온다.
- Simplex noise의 gradient는 해시로 만든 pseudo-random 값이다.
- Simplex noise는 PDE 해를 구하지 않고, 연속적인 절차적 스칼라 필드를 만든다.

## 조건부 확률과 가능도 관점

`d(x, y, t)` 또는 `d(x, y, z, t)` 자체는 확률이 아니다. 확률 모델의 관점에서는 score, logit, energy 같은 원시 스칼라 값에 가깝다.

occupancy 확률로 쓰려면 변환이 필요하다.

```text
P(inside | p) = sigmoid(d(p) - threshold)
```

등가선 또는 등가면은 다음 조건으로 정의된다.

```text
d(p) = threshold
```

이는 분류 모델에서 decision boundary에 해당한다.

정리하면 Simplex noise는 가능도 계산 그 자체가 아니라, 가능도나 occupancy 확률의 입력으로 쓸 수 있는 연속 score field 생성 방식이다.

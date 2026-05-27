# 게임에서 지형을 만들 때 쓰는 특수한 수학 기법 #프로그래밍 #펄린노이즈 #수학 #절차적생성
# https://www.youtube.com/shorts/kY9TYQYxCZM

import perlin
import numpy as np
import matplotlib.pyplot as plt

DOMAIN_MAX = 1
CELL_DIVISION = 100
BASE_DIVISION = 10


def _plot_perlin_surface(
    X_fine: np.ndarray,
    Y_fine: np.ndarray,
    Z: np.ndarray,
    cell_division: int,
    pngname: str = None,
) -> None:
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(
        X_fine,
        Y_fine,
        Z,
        cmap="viridis",
        rcount=cell_division,
        ccount=cell_division,
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("noise")
    ax.set_aspect("equal")
    # plt.show()
    plt.savefig(pngname)


def test_perlin() -> None:
    generator = perlin.Perlin(6789)

    x_fine: np.ndarray = np.linspace(0, DOMAIN_MAX, CELL_DIVISION)
    y_fine: np.ndarray = np.linspace(0, DOMAIN_MAX, CELL_DIVISION)
    X_fine, Y_fine = np.meshgrid(x_fine, y_fine)

    Z: np.ndarray = np.zeros_like(X_fine)
    for row in range(Z.shape[0]):
        for col in range(Z.shape[1]):
            Z[row, col] = (
                generator.noise(
                    X_fine[row, col] * BASE_DIVISION,
                    Y_fine[row, col] * BASE_DIVISION,
                )
                / BASE_DIVISION
            )

    _plot_perlin_surface(X_fine, Y_fine, Z, cell_division=CELL_DIVISION, pngname="1test_perlin")


def my_perlin() -> None:

    cell_size: float = DOMAIN_MAX / (BASE_DIVISION - 1)

    random_angles: np.ndarray = np.random.rand(BASE_DIVISION, BASE_DIVISION) * 2 * np.pi

    x_fine: np.ndarray = np.linspace(0, DOMAIN_MAX, CELL_DIVISION)
    y_fine: np.ndarray = np.linspace(0, DOMAIN_MAX, CELL_DIVISION)
    X_fine, Y_fine = np.meshgrid(x_fine, y_fine)

    # 파인 그리드의 각 점은 4개의 기점에서 해당 내부 점까지의 벡터와 기점의 u,v 벡터와의 내적을 계산하여 합산하여 계산한다.

    def fade(t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    def dot_at_corner(ix: int, iy: int, px: float, py: float) -> float:
        dx: float = px - ix * cell_size
        dy: float = py - iy * cell_size
        angle = random_angles[iy, ix]
        return np.cos(angle) * dx + np.sin(angle) * dy

    Z = np.zeros_like(X_fine)
    for row in range(Z.shape[0]):
        for col in range(Z.shape[1]):
            px, py = X_fine[row, col], Y_fine[row, col]

            ix: int = min(int(px / cell_size), BASE_DIVISION - 2)
            iy: int = min(int(py / cell_size), BASE_DIVISION - 2)

            tx = (px - ix * cell_size) / cell_size
            ty = (py - iy * cell_size) / cell_size

            n00: float = dot_at_corner(ix, iy, px, py)
            n10: float = dot_at_corner(ix + 1, iy, px, py)
            n01: float = dot_at_corner(ix, iy + 1, px, py)
            n11: float = dot_at_corner(ix + 1, iy + 1, px, py)

            sx, sy = fade(tx), fade(ty)
            nx0: float = n00 + sx * (n10 - n00)
            nx1: float = n01 + sx * (n11 - n01)
            Z[row, col] = nx0 + sy * (nx1 - nx0)

    _plot_perlin_surface(X_fine, Y_fine, Z, cell_division=CELL_DIVISION, pngname="2my_perlin")


def main() -> None:
    print("perlin.Perlin()")
    test_perlin()
    print("-" * 80)
    print()

    print("my_perlin()")
    my_perlin()
    print()
    print("-" * 80)


if __name__ == "__main__":
    main()

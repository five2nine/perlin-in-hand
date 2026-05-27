from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import numpy as np

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
COMMON_DIR = PROJECT_ROOT / "implementations" / "terrain_generation_common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from terrain_npz_loader import load_terrain_npz, newest_export  # noqa: E402


PALETTES: dict[str, list[tuple[float, tuple[int, int, int]]]] = {
    "terrain": [
        (0.0, (22, 46, 86)),
        (0.18, (44, 104, 93)),
        (0.38, (77, 136, 72)),
        (0.62, (151, 137, 88)),
        (0.82, (185, 178, 150)),
        (1.0, (242, 243, 238)),
    ],
    "grayscale": [
        (0.0, (18, 18, 20)),
        (1.0, (236, 236, 232)),
    ],
    "heat": [
        (0.0, (31, 25, 49)),
        (0.28, (97, 46, 97)),
        (0.55, (190, 71, 71)),
        (0.78, (232, 151, 76)),
        (1.0, (250, 236, 168)),
    ],
}


def parse_window_size(value: str) -> tuple[int, int]:
    parts = value.lower().replace(",", "x").split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("window size must look like 1280x900")
    width, height = int(parts[0]), int(parts[1])
    if width < 320 or height < 240:
        raise argparse.ArgumentTypeError("window size must be at least 320x240")
    return width, height


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CPU/Pygame viewer for exported terrain_generation .npz heightmaps.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to an exported terrain .npz file. Defaults to the newest export.",
    )
    parser.add_argument(
        "--palette",
        choices=tuple(PALETTES),
        default="terrain",
        help="Initial heightmap color palette.",
    )
    parser.add_argument(
        "--window-size",
        type=parse_window_size,
        default=(1280, 900),
        help="Initial window size, for example 1280x900.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Load the file, build the CPU surface, print a summary, and exit.",
    )
    return parser.parse_args()


def normalize_heights(heights: np.ndarray) -> np.ndarray:
    height_min = float(np.min(heights))
    height_max = float(np.max(heights))
    span = height_max - height_min
    if span <= 1e-8:
        return np.zeros_like(heights, dtype="f4")
    return ((heights - height_min) / span).astype("f4")


def colorize_heights(heights: np.ndarray, palette_name: str) -> np.ndarray:
    values = normalize_heights(heights)
    stops = PALETTES[palette_name]
    stop_positions = np.array([stop[0] for stop in stops], dtype="f4")
    stop_colors = np.array([stop[1] for stop in stops], dtype="f4")

    flat = values.reshape(-1)
    rgb = np.empty((flat.size, 3), dtype="f4")
    for channel in range(3):
        rgb[:, channel] = np.interp(flat, stop_positions, stop_colors[:, channel])
    return np.clip(rgb.reshape((*values.shape, 3)), 0, 255).astype("u1")


def make_height_surface(heights: np.ndarray, palette_name: str) -> pygame.Surface:
    rgb = colorize_heights(heights, palette_name)
    surface_data = np.transpose(rgb, (1, 0, 2))
    return pygame.surfarray.make_surface(surface_data)


class PygameTerrainNpzViewer:
    def __init__(
        self,
        terrain: dict[str, object],
        palette_name: str,
        window_size: tuple[int, int],
    ) -> None:
        self.terrain = terrain
        self.path = Path(terrain["path"])
        self.rows = int(terrain["rows"])
        self.cols = int(terrain["cols"])
        self.heights = np.asarray(terrain["heights_grid"], dtype="f4")
        self.metadata = dict(terrain["metadata"])

        self.palette_names = list(PALETTES)
        self.palette_index = self.palette_names.index(palette_name)
        self.height_surface = make_height_surface(self.heights, self.palette_name)

        self.window_size = window_size
        self.zoom = 1.0
        self.offset = np.array([0.0, 0.0], dtype="f4")
        self.dragging = False

        pygame.init()
        pygame.display.set_caption("Pygame Terrain NPZ Viewer")
        self.screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 16)
        self.small_font = pygame.font.SysFont("consolas", 14)

    @property
    def palette_name(self) -> str:
        return self.palette_names[self.palette_index]

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    running = self.handle_event(event)
                    if not running:
                        break

            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.VIDEORESIZE:
            self.window_size = (max(320, event.w), max(240, event.h))
            self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                return False
            if event.key == pygame.K_r:
                self.reset_view()
            elif event.key == pygame.K_c:
                self.cycle_palette()
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self.adjust_zoom(1.1)
            elif event.key == pygame.K_MINUS:
                self.adjust_zoom(1.0 / 1.1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.offset += np.array(event.rel, dtype="f4")
        elif event.type == pygame.MOUSEWHEEL:
            self.adjust_zoom(1.12 if event.y > 0 else 1.0 / 1.12)
        return True

    def reset_view(self) -> None:
        self.zoom = 1.0
        self.offset[:] = 0.0

    def adjust_zoom(self, factor: float) -> None:
        self.zoom = float(np.clip(self.zoom * factor, 0.1, 32.0))

    def cycle_palette(self) -> None:
        self.palette_index = (self.palette_index + 1) % len(self.palette_names)
        self.height_surface = make_height_surface(self.heights, self.palette_name)

    def image_rect(self) -> pygame.Rect:
        width, height = self.screen.get_size()
        margin = 24
        fit_scale = min((width - margin * 2) / self.cols, (height - margin * 2) / self.rows)
        scale = max(1e-4, fit_scale * self.zoom)
        image_width = max(1, int(round(self.cols * scale)))
        image_height = max(1, int(round(self.rows * scale)))
        rect = pygame.Rect(0, 0, image_width, image_height)
        rect.center = (
            int(width * 0.5 + self.offset[0]),
            int(height * 0.5 + self.offset[1]),
        )
        return rect

    def draw(self) -> None:
        self.screen.fill((16, 17, 19))
        rect = self.image_rect()
        scaled = pygame.transform.smoothscale(self.height_surface, rect.size)
        self.screen.blit(scaled, rect)
        pygame.draw.rect(self.screen, (215, 219, 216), rect, width=1)
        self.draw_overlay()

    def draw_overlay(self) -> None:
        fps = self.clock.get_fps()
        lines = [
            f"{self.path.name}",
            f"grid={self.rows}x{self.cols}  palette={self.palette_name}  zoom={self.zoom:.2f}x",
            f"height={float(np.min(self.heights)):.6g}..{float(np.max(self.heights)):.6g}  fps={fps:.1f}",
            "drag=pan  wheel/+-=zoom  C=palette  R=reset  Esc=quit",
        ]
        backend = self.metadata.get("backend")
        layer_count = self.metadata.get("layer_count")
        if backend is not None or layer_count is not None:
            layer_text = layer_count if layer_count is not None else "unknown"
            lines.insert(2, f"backend={backend or 'unknown'}  layers={layer_text}")

        padding = 10
        line_height = 20
        width = max(self.font.size(line)[0] for line in lines) + padding * 2
        height = line_height * len(lines) + padding * 2
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((8, 10, 12, 188))
        self.screen.blit(panel, (14, 14))

        y = 14 + padding
        for index, line in enumerate(lines):
            font = self.font if index == 0 else self.small_font
            color = (242, 244, 239) if index == 0 else (208, 214, 211)
            text = font.render(line, True, color)
            self.screen.blit(text, (14 + padding, y))
            y += line_height


def main() -> None:
    args = parse_args()
    path = Path(args.path).resolve() if args.path else newest_export()
    terrain = load_terrain_npz(path)
    if args.smoke:
        pygame.init()
        surface = make_height_surface(np.asarray(terrain["heights_grid"], dtype="f4"), args.palette)
        print(
            "pygame terrain viewer smoke ok: "
            f"path={Path(terrain['path']).name}, "
            f"grid={terrain['rows']}x{terrain['cols']}, "
            f"surface={surface.get_size()}, "
            f"height={terrain['height_min']:.6g}..{terrain['height_max']:.6g}"
        )
        pygame.quit()
        return

    viewer = PygameTerrainNpzViewer(terrain, args.palette, args.window_size)
    print("=" * 72)
    print("Pygame Terrain NPZ Viewer")
    print("-" * 72)
    print(f"File      : {terrain['path']}")
    print(f"Grid      : {terrain['rows']} x {terrain['cols']}")
    print(f"Height    : {terrain['height_min']:.6f} .. {terrain['height_max']:.6f}")
    print(f"Backend   : {terrain['metadata'].get('backend', 'unknown')}")
    print(f"Layers    : {terrain['metadata'].get('layer_count', 'unknown')}")
    print("-" * 72)
    print("Controls: drag pan, wheel zoom, C palette, R reset, Esc quit")
    print("=" * 72)
    viewer.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"pygame terrain npz viewer error: {exc}", file=sys.stderr)
        raise

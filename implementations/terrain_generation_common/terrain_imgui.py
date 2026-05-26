from __future__ import annotations

from collections.abc import Callable
from typing import Any

import imgui
from moderngl_window.integrations.imgui import ModernglWindowRenderer

from terrain_layers import LayerKind


class TerrainImguiPanel:
    def __init__(
        self,
        window: Any,
        backend_label: str,
        palette_names: list[str],
        get_build_ms: Callable[[], float] | None = None,
    ) -> None:
        imgui.create_context()
        io = imgui.get_io()
        io.ini_file_name = None

        style = imgui.get_style()
        style.window_rounding = 5.0
        style.frame_rounding = 4.0
        style.grab_rounding = 4.0

        self.window = window
        self.renderer = ModernglWindowRenderer(window)
        self.io = imgui.get_io()
        self.backend_label = backend_label
        self.palette_names = palette_names
        self.get_build_ms = get_build_ms
        self.panel_width = 390.0
        self.panel_height = 680.0
        self.layer_stack_height = 180.0

    @property
    def wants_mouse(self) -> bool:
        return bool(self.io.want_capture_mouse)

    def render(self, app: Any) -> None:
        self._sync_display_state()
        imgui.new_frame()
        self._draw_panel(app)
        imgui.render()
        self.renderer.render(imgui.get_draw_data())

    def shutdown(self) -> None:
        self.renderer.shutdown()

    def resize(self, width: int, height: int) -> None:
        self.renderer.resize(width, height)
        self._sync_display_state()

    def key_event(self, key: Any, action: Any, modifiers: Any) -> None:
        self.renderer.key_event(key, action, modifiers)

    def mouse_position_event(self, x: int, y: int, dx: int, dy: int) -> None:
        self._set_mouse_pos(x, y)

    def mouse_drag_event(self, x: int, y: int, dx: int, dy: int) -> None:
        self._set_mouse_pos(x, y)

    def mouse_scroll_event(self, x_offset: float, y_offset: float) -> None:
        self.io.mouse_wheel_horizontal += float(x_offset)
        self.io.mouse_wheel += float(y_offset)

    def mouse_press_event(self, x: int, y: int, button: int) -> None:
        self._set_mouse_pos(x, y)
        self._set_mouse_button(button, True)

    def mouse_release_event(self, x: int, y: int, button: int) -> None:
        self._set_mouse_pos(x, y)
        self._set_mouse_button(button, False)

    def unicode_char_entered(self, char: str) -> None:
        self.renderer.unicode_char_entered(char)

    def _sync_display_state(self) -> None:
        width, height = self.window.size
        buffer_width, buffer_height = self.window.buffer_size
        self.io.display_size = (width, height)
        self.io.display_fb_scale = (
            buffer_width / max(width, 1),
            buffer_height / max(height, 1),
        )

        margin = 16.0
        available_width = max(120.0, float(width) - margin * 2.0)
        available_height = max(160.0, float(height) - margin * 2.0)
        self.panel_width = min(390.0, available_width)
        self.panel_height = min(680.0, available_height)
        self.layer_stack_height = max(72.0, min(180.0, self.panel_height - 430.0))

    def _set_mouse_pos(self, x: int, y: int) -> None:
        viewport_x = x - (
            self.window.width - self.window.viewport_width / self.window.pixel_ratio
        ) / 2
        viewport_y = y - (
            self.window.height - self.window.viewport_height / self.window.pixel_ratio
        ) / 2
        self.io.mouse_pos = (float(viewport_x), float(viewport_y))

    def _set_mouse_button(self, button: int, pressed: bool) -> None:
        if button == self.window.mouse.left:
            self.io.mouse_down[0] = pressed
        elif button == self.window.mouse.middle:
            self.io.mouse_down[2] = pressed
        elif button == self.window.mouse.right:
            self.io.mouse_down[1] = pressed

    def _draw_panel(self, app: Any) -> None:
        imgui.set_next_window_position(16, 16, condition=imgui.ALWAYS)
        imgui.set_next_window_size(
            self.panel_width,
            self.panel_height,
            condition=imgui.ALWAYS,
        )
        imgui.begin(
            "Terrain Controls",
            flags=imgui.WINDOW_NO_COLLAPSE,
        )

        imgui.text(f"{self.backend_label} Terrain Heightfield")
        imgui.text(f"FPS: {app.fps_val:.1f}")
        if self.get_build_ms is not None:
            imgui.same_line()
            imgui.text(f"Build: {self.get_build_ms():.2f} ms")

        changed, resolution = imgui.slider_int(
            "Resolution",
            int(app.resolution),
            32,
            512,
            format="%d",
        )
        if changed:
            app.resolution = int(resolution)
            app.rebuild_grid()

        changed, palette = imgui.combo("Palette", int(app.palette), self.palette_names)
        if changed:
            app.palette = int(palette)

        if imgui.button("Reset Terrain"):
            app.stack.reset_default()
            app.selected_layer = 0
            app.upload_terrain_stack()
        imgui.same_line()
        if imgui.button("Reset Camera"):
            app.reset_camera()

        imgui.separator()
        self._draw_add_buttons(app)
        imgui.separator()
        self._draw_layer_list(app)
        imgui.separator()
        self._draw_selected_layer_editor(app)

        imgui.end()

    def _draw_add_buttons(self, app: Any) -> None:
        imgui.text(f"Layers: {len(app.stack.layers)} / 16")

        if imgui.button("Random"):
            app.add_random_layer()
        imgui.same_line()
        if imgui.button("1 Oct"):
            app.add_random_layer(force_kind=LayerKind.SIMPLE, octaves=1)
        imgui.same_line()
        if imgui.button("2 Oct"):
            app.add_random_layer(force_kind=LayerKind.SIMPLE, octaves=2)
        imgui.same_line()
        if imgui.button("3 Oct"):
            app.add_random_layer(force_kind=LayerKind.SIMPLE, octaves=3)

        if imgui.button("Valley"):
            app.add_random_layer(force_kind=LayerKind.VALLEY)
        imgui.same_line()
        if imgui.button("Billow"):
            app.add_random_layer(force_kind=LayerKind.BILLOW)
        imgui.same_line()
        if imgui.button("Ridged"):
            app.add_random_layer(force_kind=LayerKind.RIDGED)
        imgui.same_line()
        if imgui.button("Warped"):
            app.add_random_layer(force_kind=LayerKind.WARPED)

    def _draw_layer_list(self, app: Any) -> None:
        imgui.text("Layer Stack")
        imgui.begin_child("layer-stack", height=self.layer_stack_height, border=True)

        pending_delete: int | None = None
        select_width = max(80.0, imgui.get_content_region_available_width() - 58.0)
        for index, layer in enumerate(app.stack.layers):
            imgui.push_id(str(index))

            changed, enabled = imgui.checkbox("##enabled", layer.enabled)
            if changed:
                app.set_layer_enabled(index, bool(enabled))

            imgui.same_line()
            selected = index == app.selected_layer
            clicked, _ = imgui.selectable(
                f"{index:02d} {layer.summary()}",
                selected=selected,
                width=select_width,
            )
            if clicked:
                app.selected_layer = index

            imgui.same_line()
            if imgui.small_button("Del"):
                pending_delete = index

            imgui.pop_id()

        imgui.end_child()

        if pending_delete is not None:
            app.remove_layer(pending_delete)

    def _draw_selected_layer_editor(self, app: Any) -> None:
        layer = app.selected()
        if layer is None:
            imgui.text("No selected layer")
            return

        imgui.text(f"Selected: {app.selected_layer:02d} {layer.name}")

        changed, enabled = imgui.checkbox("Enabled", layer.enabled)
        if changed:
            app.set_layer_enabled(app.selected_layer, bool(enabled))

        changed, octaves = imgui.slider_int("Octaves", int(layer.octaves), 1, 3, format="%d")
        if changed:
            layer.octaves = int(octaves)
            app.upload_terrain_stack()

        self._slider_float(app, layer, "Frequency", "frequency", 0.25, 64.0, "%.2f")
        self._slider_float(app, layer, "Amplitude", "amplitude", 0.0, 0.35, "%.3f")
        self._slider_float(app, layer, "Persistence", "persistence", 0.1, 0.9, "%.2f")
        self._slider_float(app, layer, "Lacunarity", "lacunarity", 1.1, 3.5, "%.2f")
        self._slider_float(app, layer, "Valley Power", "valley_power", 0.5, 5.0, "%.2f")
        self._slider_float(app, layer, "Warp Strength", "warp_strength", 0.0, 0.2, "%.3f")
        self._slider_float(app, layer, "Warp Frequency", "warp_frequency", 0.5, 16.0, "%.2f")

    def _slider_float(
        self,
        app: Any,
        layer: Any,
        label: str,
        attr: str,
        minimum: float,
        maximum: float,
        fmt: str,
    ) -> None:
        changed, value = imgui.slider_float(
            label,
            float(getattr(layer, attr)),
            minimum,
            maximum,
            format=fmt,
        )
        if changed:
            setattr(layer, attr, float(value))
            app.upload_terrain_stack()

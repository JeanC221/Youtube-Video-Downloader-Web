import flet as ft
from typing import Callable, Optional

# --- Custom Components ---

class StatusChip(ft.Container):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self._status = "ready" # ready, working, done, error
        
        self.icon_map = {
            "ready": ft.Icons.CHECK_CIRCLE_OUTLINE,
            "working": ft.Icons.DOWNLOADING,
            "done": ft.Icons.CHECK_CIRCLE,
            "error": ft.Icons.ERROR_OUTLINE
        }
        
        self.text_map = {
            "ready": "Listo",
            "working": "Procesando...",
            "done": "Completado",
            "error": "Error"
        }
        
        self.color_map = {
            "ready": theme.text_secondary,
            "working": theme.primary_color,
            "done": theme.success_color,
            "error": theme.error_color
        }
        
        # Initial state
        self.status_icon = ft.Icon(self.icon_map["ready"], size=16, color=self.color_map["ready"])
        self.status_text = ft.Text(self.text_map["ready"], size=12, color=self.color_map["ready"], weight=ft.FontWeight.W_500)
        
        self.content = ft.Row(
            [self.status_icon, self.status_text],
            spacing=5,
            alignment=ft.MainAxisAlignment.CENTER
        )
        
        self.padding = ft.padding.symmetric(horizontal=12, vertical=6)
        self.border_radius = 20
        self.bgcolor = ft.Colors.with_opacity(0.1, self.color_map["ready"])
        self.border = ft.border.all(1, ft.Colors.with_opacity(0.2, self.color_map["ready"]))
        self.animate = ft.Animation(300, "easeOut")
        
    def set_status(self, status: str, custom_text: str = None):
        if status not in self.icon_map: return
        
        self._status = status
        color = self.color_map[status]
        
        # Update styling
        self.bgcolor = ft.Colors.with_opacity(0.1, color)
        self.border = ft.border.all(1, ft.Colors.with_opacity(0.2, color))
        
        # Update content
        self.status_icon.name = self.icon_map[status]
        self.status_icon.color = color
        self.status_text.value = custom_text if custom_text else self.text_map[status]
        self.status_text.color = color
        
        self.update()

class ModernButton(ft.Container):
    def __init__(
        self,
        text: str,
        on_click: Optional[Callable] = None,
        icon: str = None, # Expect string name like ft.Icons.DOWNLOAD
        width: Optional[int] = None,
        height: int = 50,
        gradient_colors: list = None,
        disabled: bool = False,
        tooltip: str = None
    ):
        super().__init__()
        self.text = text
        self.base_on_click = on_click
        self.icon_name = icon
        self.width = width
        self.height = height
        self.gradient_colors = gradient_colors or ["#ec4899", "#a855f7"]
        self.is_disabled = disabled
        self.tooltip = tooltip
        self._scale = 1.0
        
        # Build content
        content_items = []
        if self.icon_name:
            content_items.append(ft.Icon(self.icon_name, color="white", size=20))
            if text: content_items.append(ft.Container(width=8))
        
        if text:
            content_items.append(ft.Text(self.text, size=16, weight=ft.FontWeight.BOLD, color="white"))
            
        self.content = ft.Row(content_items, alignment=ft.MainAxisAlignment.CENTER, spacing=0)
        
        # Styling
        self.gradient = ft.LinearGradient(
            colors=self.gradient_colors,
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right
        )
        self.border_radius = self.height // 2
        self.on_click = self._handle_click if not disabled else None
        self.on_hover = self._on_hover
        self.animate_scale = ft.Animation(100, "easeOut")
        self.scale = 1.0
        self.opacity = 0.6 if disabled else 1.0
        self.shadow = ft.BoxShadow(
            blur_radius=10,
            color=ft.Colors.with_opacity(0.3, self.gradient_colors[0]),
            offset=ft.Offset(0, 4)
        )
        self.ink = True
        
    def _handle_click(self, e):
        if self.base_on_click:
            self.scale = 0.95
            self.update()
            import threading
            def reset():
                import time
                time.sleep(0.1)
                self.scale = 1.0
                self.update()
            threading.Thread(target=reset, daemon=True).start()
            self.base_on_click(e)
            
    def _on_hover(self, e):
        if not self.is_disabled:
            self.scale = 1.02 if e.data == "true" else 1.0
            self.update()
            
    def set_disabled(self, disabled: bool):
        self.is_disabled = disabled
        self.opacity = 0.6 if disabled else 1.0
        self.on_click = None if disabled else self._handle_click
        self.update()

class TooltipIconButton(ft.IconButton):
    def __init__(self, icon, on_click, tooltip, theme, icon_color=None):
        super().__init__()
        self.icon = icon
        self.on_click = on_click
        self.tooltip = tooltip
        self.icon_color = icon_color or theme.text_secondary
        self.selected_icon_color = theme.primary_color
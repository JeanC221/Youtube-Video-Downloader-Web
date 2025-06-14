import flet as ft
from typing import Callable, Optional

class ModernButton(ft.Control):
    def __init__(
        self,
        text: str,
        on_click: Optional[Callable] = None,
        icon: Optional[ft.icons] = None,
        width: Optional[int] = None,
        height: int = 50,
        gradient_colors: list = None,
        disabled: bool = False
    ):
        super().__init__()
        self.text = text
        self.on_click = on_click
        self.icon = icon
        self.width = width
        self.height = height
        self.gradient_colors = gradient_colors or ["#ec4899", "#a855f7"]
        self.disabled = disabled
        self._scale = 1.0
    
    def build(self):
        content = []
        
        if self.icon:
            content.append(
                ft.Icon(self.icon, color="white", size=20)
            )
            content.append(ft.Container(width=8))
        
        content.append(
            ft.Text(
                self.text,
                size=16,
                weight=ft.FontWeight.BOLD,
                color="white"
            )
        )
        
        return ft.Container(
            content=ft.Row(
                content,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0
            ),
            width=self.width,
            height=self.height,
            gradient=ft.LinearGradient(
                colors=self.gradient_colors,
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right
            ),
            border_radius=self.height // 2,
            on_click=self._handle_click if not self.disabled else None,
            on_hover=self._on_hover,
            animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.animation.Animation(150, ft.AnimationCurve.EASE_OUT),
            scale=self._scale,
            opacity=0.5 if self.disabled else 1.0,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.colors.with_opacity(0.3, self.gradient_colors[0]),
                offset=ft.Offset(0, 4)
            )
        )
    
    def _handle_click(self, e):
        if self.on_click:
            self.scale = 0.95
            self.update()
            self.page.run_task(self._reset_scale)
            self.on_click(e)
    
    async def _reset_scale(self):
        await self.page.sleep(0.1)
        self.scale = 1.0
        self.update()
    
    def _on_hover(self, e):
        if not self.disabled:
            self.scale = 1.05 if e.data == "true" else 1.0
            self.update()
    
    @property
    def scale(self):
        return self._scale
    
    @scale.setter
    def scale(self, value):
        self._scale = value
        if hasattr(self, 'controls') and self.controls:
            self.controls[0].scale = value


class InfoCard(ft.Control):
    def __init__(
        self,
        title: str,
        theme,
        content: Optional[ft.Control] = None,
        icon: Optional[ft.icons] = None,
        elevation: int = 2
    ):
        super().__init__()
        self.title = title
        self.theme = theme
        self.content = content
        self.icon = icon
        self.elevation = elevation
    
    def build(self):
        header_content = []
        
        if self.icon:
            header_content.append(
                ft.Icon(
                    self.icon,
                    color=self.theme.primary_color,
                    size=24
                )
            )
            header_content.append(ft.Container(width=10))
        
        header_content.append(
            ft.Text(
                self.title,
                size=18,
                weight=ft.FontWeight.BOLD,
                color=self.theme.text_primary
            )
        )
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row(header_content),
                    ft.Divider(color=self.theme.border_color),
                    self.content or ft.Container()
                ], spacing=10),
                padding=20,
                bgcolor=self.theme.card_color
            ),
            elevation=self.elevation,
            color=self.theme.card_color
        )


class AnimatedProgressBar(ft.Control):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self._progress = 0
        self._text = "Listo para descargar"
    
    def build(self):
        self.progress_bar = ft.ProgressBar(
            value=0,
            height=8,
            color=self.theme.primary_color,
            bgcolor=self.theme.border_color,
            border_radius=4
        )
        
        self.progress_text = ft.Text(
            self._text,
            size=14,
            color=self.theme.text_secondary
        )
        
        return ft.Column([
            ft.Container(
                content=self.progress_bar,
                border_radius=4,
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=4,
                    color=ft.colors.with_opacity(0.1, self.theme.primary_color),
                    offset=ft.Offset(0, 2)
                )
            ),
            ft.Container(height=5),
            ft.Row([
                self.progress_text,
                ft.Container(expand=True),
                ft.Text(
                    f"{int(self._progress * 100)}%",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.primary_color
                )
            ])
        ])
    
    def update_progress(self, value: float, text: str = None):
        self._progress = value
        self.progress_bar.value = value
        
        if text:
            self._text = text
            self.progress_text.value = text
        
        if hasattr(self, 'controls') and self.controls:
            percentage_text = self.controls[0].content.controls[2].controls[2]
            percentage_text.value = f"{int(value * 100)}%"
        
        self.update()


class HistoryItem(ft.Control):
    def __init__(self, entry: dict, theme, on_redownload: Callable):
        super().__init__()
        self.entry = entry
        self.theme = theme
        self.on_redownload = on_redownload
    
    def build(self):
        format_icon = ft.icons.MUSIC_NOTE if self.entry.get('format') == 'mp3' else ft.icons.VIDEO_FILE
        format_color = self.theme.accent_color if self.entry.get('format') == 'mp3' else self.theme.primary_color
        
        title = self.entry.get('title', 'Desconocido')
        if len(title) > 35:
            title = title[:32] + "..."
        
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(format_icon, color=format_color, size=20),
                    bgcolor=ft.colors.with_opacity(0.1, format_color),
                    padding=10,
                    border_radius=10
                ),
                
                ft.Column([
                    ft.Text(
                        title,
                        size=14,
                        weight=ft.FontWeight.W_500,
                        color=self.theme.text_primary
                    ),
                    ft.Text(
                        f"{self.entry.get('format', '').upper()} • {self.entry.get('date', '')}",
                        size=12,
                        color=self.theme.text_secondary
                    )
                ], spacing=2, expand=True),
                
                ft.IconButton(
                    icon=ft.icons.DOWNLOAD,
                    icon_color=self.theme.primary_color,
                    icon_size=18,
                    tooltip="Descargar de nuevo",
                    on_click=lambda _: self.on_redownload(self.entry.get('url', ''))
                )
            ], spacing=15),
            padding=ft.padding.all(15),
            bgcolor=self.theme.surface_color,
            border_radius=12,
            on_hover=self._on_hover,
            animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT)
        )
    
    def _on_hover(self, e):
        e.control.bgcolor = self.theme.hover_color if e.data == "true" else self.theme.surface_color
        e.control.update()
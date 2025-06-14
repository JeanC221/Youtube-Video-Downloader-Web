import flet as ft

class AppTheme:
    def __init__(self, is_dark=False):
        self.is_dark = is_dark
        self._define_colors()
    
    def _define_colors(self):
        if self.is_dark:
            # Tema oscuro
            self.bg_color = "#0f172a"
            self.surface_color = "#1e293b"
            self.card_color = "#334155"
            self.primary_color = "#ec4899"
            self.primary_gradient = ["#ec4899", "#a855f7"]
            self.secondary_color = "#8b5cf6"
            self.accent_color = "#06b6d4"
            self.text_primary = "#f1f5f9"
            self.text_secondary = "#94a3b8"
            self.text_disabled = "#64748b"
            self.border_color = "#475569"
            self.hover_color = "#475569"
            self.error_color = "#ef4444"
            self.success_color = "#10b981"
            self.warning_color = "#f59e0b"
            self.info_color = "#3b82f6"
            self.shadow_color = "rgba(0,0,0,0.7)"
            self.overlay_color = "rgba(0,0,0,0.5)"
        else:
            # Tema claro
            self.bg_color = "#ffffff"
            self.surface_color = "#f8fafc"
            self.card_color = "#ffffff"
            self.primary_color = "#ec4899"
            self.primary_gradient = ["#ec4899", "#a855f7"]
            self.secondary_color = "#8b5cf6"
            self.accent_color = "#06b6d4"
            self.text_primary = "#1e293b"
            self.text_secondary = "#64748b"
            self.text_disabled = "#94a3b8"
            self.border_color = "#e2e8f0"
            self.hover_color = "#f1f5f9"
            self.error_color = "#ef4444"
            self.success_color = "#10b981"
            self.warning_color = "#f59e0b"
            self.info_color = "#3b82f6"
            self.shadow_color = "rgba(0,0,0,0.1)"
            self.overlay_color = "rgba(0,0,0,0.3)"
    
    def toggle(self):
        self.is_dark = not self.is_dark
        self._define_colors()
    
    def get_flet_theme_mode(self):
        return ft.ThemeMode.DARK if self.is_dark else ft.ThemeMode.LIGHT
    
    def apply_to_page(self, page: ft.Page):
        page.theme_mode = self.get_flet_theme_mode()
        page.bgcolor = self.bg_color
        page.update()
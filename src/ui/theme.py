import flet as ft

class AppTheme:
    def __init__(self, is_dark=True):
        self.is_dark = is_dark
        self._define_colors()
    
    def _define_colors(self):
        if self.is_dark:
            # Tema oscuro PREMIUM - Deep Navy & Electric Blue/Pink
            self.bg_color = "#0B1120"  # Muy oscuro, casi negro
            self.surface_color = "#1E293B" # Grises azulados
            self.card_color = "#334155"
            
            # Gradientes y acentos
            self.primary_color = "#F472B6" # Pink 400
            self.secondary_color = "#22D3EE" # Cyan 400
            self.accent_color = "#818CF8" # Indigo 400
            
            self.primary_gradient = [
                "#EC4899",  # Pink 500
                "#9333EA",  # Purple 600
                "#4F46E5",  # Indigo 600
            ]
            
            # Texto
            self.text_primary = "#F8FAFC"
            self.text_secondary = "#94A3B8"
            self.text_disabled = "#475569"
            
            # UI Elements
            self.border_color = "#334155"
            self.hover_color = "#334155"
            self.input_bgcolor = "#1E293B"
            
            # Estados
            self.error_color = "#EF4444"
            self.success_color = "#10B981"
            self.warning_color = "#F59E0B"
            self.info_color = "#3B82F6"
            
            # Missing attributes fixed
            self.shadow_color = ft.Colors.with_opacity(0.5, "#000000")
            self.overlay_color = ft.Colors.with_opacity(0.5, "#000000")
            
        else:
            # Tema claro PREMIUM - Clean White & Soft Gradients
            self.bg_color = "#F8FAFC"
            self.surface_color = "#FFFFFF"
            self.card_color = "#FFFFFF"
            
            # Gradientes y acentos
            self.primary_color = "#EC4899"
            self.secondary_color = "#06B6D4"
            self.accent_color = "#6366F1"
            
            self.primary_gradient = [
                "#EC4899",  # Pink 500
                "#A855F7",  # Purple 500
                "#6366F1",  # Indigo 500
            ]
            
            # Texto
            self.text_primary = "#0F172A"
            self.text_secondary = "#64748B"
            self.text_disabled = "#CBD5E1"
            
            # UI Elements
            self.border_color = "#E2E8F0"
            self.hover_color = "#F1F5F9"
            self.input_bgcolor = "#F1F5F9"
            
            # Estados
            self.error_color = "#EF4444"
            self.success_color = "#10B981"
            self.warning_color = "#F59E0B"
            self.info_color = "#3B82F6"
            
            # Missing attributes fixed
            self.shadow_color = ft.Colors.with_opacity(0.1, "#000000")
            self.overlay_color = ft.Colors.with_opacity(0.3, "#000000")

    def toggle(self):
        self.is_dark = not self.is_dark
        self._define_colors()
    
    def get_flet_theme_mode(self):
        return ft.ThemeMode.DARK if self.is_dark else ft.ThemeMode.LIGHT
    
    def apply_to_page(self, page: ft.Page):
        page.theme_mode = self.get_flet_theme_mode()
        page.bgcolor = self.bg_color
        page.update()
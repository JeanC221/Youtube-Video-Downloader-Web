import customtkinter as ctk

class AppTheme:
    def __init__(self, is_dark=False):
        self.is_dark = is_dark
        self.update_theme()
    
    def update_theme(self):
        ctk.set_appearance_mode("dark" if self.is_dark else "light")
        
        # Colores personalizados para el tema
        if self.is_dark:
            self.accent_color = "#ff4081"  
            self.button_hover_color = "#f50057"
            self.card_color = "#1e1e30"
            self.error_color = "#f44336"
            self.success_color = "#4caf50"
            self.warning_color = "#ff9800"
            self.text_color = ["#DCE4EE", "#DCE4EE"]  # [modo claro, modo oscuro]
            self.link_color = "#00b0ff"
        else:
            self.accent_color = "#e91e63"  
            self.button_hover_color = "#c2185b"
            self.card_color = "#ffffff"
            self.error_color = "#f44336"
            self.success_color = "#4caf50" 
            self.warning_color = "#ff9800"
            self.text_color = ["#1a1b26", "#DCE4EE"]  # [modo claro, modo oscuro]
            self.link_color = "#1976d2"
    
    def toggle(self):
        self.is_dark = not self.is_dark
        self.update_theme()
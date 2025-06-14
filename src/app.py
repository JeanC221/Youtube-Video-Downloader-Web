import flet as ft
from src.ui.main_window import MainWindow

class Application:
    def __init__(self):
        self.page = None
    
    def main(self, page: ft.Page):
        """Configurar y ejecutar la aplicación"""
        self.page = page
        
        # Configuración de la ventana
        page.title = "YouTube Video Downloader"
        
        # Configurar tamaño de ventana (sin window_center)
        page.window_width = 1100
        page.window_height = 750
        page.window_min_width = 900
        page.window_min_height = 650
        
        # Centrar ventana manualmente si es posible
        try:
            page.window_center()
        except AttributeError:
            # Si window_center no existe, continuar sin centrar
            pass
        
        # Tema
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = "#ffffff"
        page.padding = 0
        
        try:
            # Crear y agregar ventana principal
            main_window = MainWindow(page)
            page.add(main_window)
        except Exception as e:
            # Mostrar error si algo falla
            page.add(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ERROR, size=48, color="red"),
                        ft.Text(f"Error al cargar la aplicación:", size=20),
                        ft.Text(str(e), size=14),
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    expand=True
                )
            )
        
        page.update()
    
    def run(self):
        """Ejecutar la aplicación"""
        try:
            ft.app(target=self.main, assets_dir="assets")
        except Exception as e:
            print(f"Error al ejecutar la aplicación: {e}")
            # Intentar sin assets_dir
            ft.app(target=self.main)
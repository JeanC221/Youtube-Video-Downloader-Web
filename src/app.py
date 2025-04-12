import customtkinter as ctk
from src.ui.main_window import MainWindow

class Application:
    def __init__(self):
        # Configurar tema y apariencia de CustomTkinter
        ctk.set_appearance_mode("light")  # Opciones: "Light", "Dark", "System"
        ctk.set_default_color_theme("blue")  # Temas: blue, dark-blue, green
        
        # Crear ventana principal
        self.root = ctk.CTk()
        self.root.title("YouTube Video Downloader")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)
        
        # Crear la interfaz principal
        self.main_window = MainWindow(self.root)
    
    def run(self):
        self.root.mainloop()
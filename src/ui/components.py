import tkinter as tk
from tkinter import ttk

class RoundedButton(tk.Canvas):
    """Botón con esquinas redondeadas y efectos de hover mejorados"""
    def __init__(self, parent, text, command=None, width=120, height=36, 
                 bg_color="#4f46e5", fg_color="#ffffff", corner_radius=18,  # Radio más redondeado
                 hover_color=None, **kwargs):
        super().__init__(parent, width=width, height=height, 
                         highlightthickness=0, **kwargs)
        
        # Propiedades
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color or self._lighten_color(bg_color, 0.1)
        self.corner_radius = corner_radius
        self.command = command
        
        # Dibujar estado inicial con sombra
        self.create_oval(3, 3, corner_radius*2+3, corner_radius*2+3, 
                         fill=self._darken_color(bg_color, 0.2), outline="")
        self.create_oval(width-corner_radius*2-3, 3, width-3, corner_radius*2+3, 
                         fill=self._darken_color(bg_color, 0.2), outline="")
        self.create_oval(3, height-corner_radius*2-3, corner_radius*2+3, height-3, 
                         fill=self._darken_color(bg_color, 0.2), outline="")
        self.create_oval(width-corner_radius*2-3, height-corner_radius*2-3, width-3, height-3, 
                         fill=self._darken_color(bg_color, 0.2), outline="")
        self.create_rectangle(corner_radius+3, 3, width-corner_radius-3, corner_radius*2+3, 
                             fill=self._darken_color(bg_color, 0.2), outline="")
        self.create_rectangle(3, corner_radius+3, width-3, height-corner_radius-3, 
                             fill=self._darken_color(bg_color, 0.2), outline="")
        self.create_rectangle(corner_radius+3, height-corner_radius*2-3, width-corner_radius-3, height-3, 
                             fill=self._darken_color(bg_color, 0.2), outline="")
        
        # Botón principal
        self.rect_id = self.create_rounded_rect(0, 0, width, height, 
                                               corner_radius, fill=bg_color, outline="")
        self.text_id = self.create_text(width/2, height/2, text=text, 
                                       fill=fg_color, font=("Helvetica", 10, "bold"))
        
        # Eventos
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)
        
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Crea un rectángulo redondeado"""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
        
    def _on_enter(self, event):
        self.itemconfig(self.rect_id, fill=self.hover_color)
        self.config(cursor="hand2")
        
    def _on_leave(self, event):
        self.itemconfig(self.rect_id, fill=self.bg_color)
        self.config(cursor="")
        
    def _on_click(self, event):
        pressed_color = self._darken_color(self.bg_color, 0.15)
        self.itemconfig(self.rect_id, fill=pressed_color)
        
    def _on_release(self, event):
        self.itemconfig(self.rect_id, fill=self.hover_color)
        if self.command:
            self.command()
    
    def _lighten_color(self, color, factor=0.1):
        """Aclarar un color hex"""
        hex_color = color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = [min(255, int(c + (255 - c) * factor)) for c in rgb]
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
    def _darken_color(self, color, factor=0.1):
        """Oscurecer un color hex"""
        hex_color = color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = [max(0, int(c * (1 - factor))) for c in rgb]
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def configure(self, **kwargs):
        """Sobreescribir configure para actualizar apariencia del botón"""
        if 'bg' in kwargs:
            self.bg_color = kwargs.pop('bg')
            self.itemconfig(self.rect_id, fill=self.bg_color)
            
        if 'fg' in kwargs:
            self.fg_color = kwargs.pop('fg')
            self.itemconfig(self.text_id, fill=self.fg_color)
            
        if 'text' in kwargs:
            self.itemconfig(self.text_id, text=kwargs.pop('text'))
            
        if 'state' in kwargs:
            if kwargs['state'] == tk.DISABLED:
                self.itemconfig(self.rect_id, fill=self._darken_color(self.bg_color, 0.3))
                self.unbind("<Enter>")
                self.unbind("<Leave>")
                self.unbind("<Button-1>")
                self.unbind("<ButtonRelease-1>")
            else:
                self.itemconfig(self.rect_id, fill=self.bg_color)
                self.bind("<Enter>", self._on_enter)
                self.bind("<Leave>", self._on_leave)
                self.bind("<Button-1>", self._on_click)
                self.bind("<ButtonRelease-1>", self._on_release)
            kwargs.pop('state')
            
        super().configure(**kwargs)


class HoverLabel(ttk.Label):
    """Etiqueta que cambia de color al pasar el ratón"""
    def __init__(self, parent, **kwargs):
        self.hover_fg = kwargs.pop('hover_fg', None)
        self.normal_fg = kwargs.get('foreground', None)
        self.callback = kwargs.pop('command', None)
        
        super().__init__(parent, **kwargs)
        
        if self.hover_fg and self.callback:
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self.bind("<Button-1>", self._on_click)
            self.configure(cursor="hand2")
            
    def _on_enter(self, event):
        if self.hover_fg:
            self.configure(foreground=self.hover_fg)
            
    def _on_leave(self, event):
        if self.normal_fg:
            self.configure(foreground=self.normal_fg)
            
    def _on_click(self, event):
        if self.callback:
            self.callback()


class RoundedFrame(ttk.Frame):
    """Marco con esquinas redondeadas para tarjetas"""
    def __init__(self, parent, **kwargs):
        self.corner_radius = kwargs.pop('corner_radius', 15)
        self.bg_color = kwargs.pop('bg_color', "#ffffff")
        self.border_color = kwargs.pop('border_color', "#eeeeee")
        
        super().__init__(parent, **kwargs)
        
        # Añadir una capa de Canvas para redondear
        self.canvas = tk.Canvas(self, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Crear la forma redondeada
        self.canvas.update_idletasks()  # Asegurarse de que el canvas tiene dimensiones
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Si el widget aún no tiene tamaño, asignar tamaño predeterminado
        if width == 0:
            width = 200
        if height == 0:
            height = 100
            
        # Crear marco redondeado
        self.canvas.create_rounded_rect = lambda x1, y1, x2, y2, r: self.canvas.create_polygon(
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2,
            x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1,
            smooth=True
        )
        
        # Dibujar borde redondeado
        self.shape_id = self.canvas.create_rounded_rect(
            0, 0, width, height, self.corner_radius, 
            fill=self.bg_color, outline=self.border_color, width=1
        )
        
        # Actualizar cuando cambie el tamaño
        self.bind("<Configure>", self._on_configure)
    
    def _on_configure(self, event):
        """Actualizar forma cuando cambia el tamaño"""
        width = event.width
        height = event.height
        
        # Redibujar la forma
        self.canvas.delete(self.shape_id)
        self.shape_id = self.canvas.create_rounded_rect(
            0, 0, width, height, self.corner_radius,
            fill=self.bg_color, outline=self.border_color, width=1
        )
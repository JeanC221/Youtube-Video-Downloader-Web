import flet as ft
import inspect

print("--- Flet Introspection ---")
print(f"Flet version: {ft.version if hasattr(ft, 'version') else 'unknown'}")

attrs = [
    'colors', 'Colors',
    'icons', 'Icons',
    'animation', 'Animation',
    'border', 'Border',
    'box_shadow', 'BoxShadow',
    'font_weight', 'FontWeight',
    'image_fit', 'ImageFit'
]

for attr in attrs:
    if hasattr(ft, attr):
        print(f"ft.{attr}: EXISTS ({type(getattr(ft, attr))})")
    else:
        print(f"ft.{attr}: MISSING")

# Check for with_opacity
try:
    if hasattr(ft, 'colors') and hasattr(ft.colors, 'with_opacity'):
        print("ft.colors.with_opacity: EXISTS")
    else:
        print("ft.colors.with_opacity: MISSING")
except:
    pass

try:
    if hasattr(ft, 'Colors') and hasattr(ft.Colors, 'with_opacity'):
        print("ft.Colors.with_opacity: EXISTS")
    else:
        print("ft.Colors.with_opacity: MISSING")
except:
    pass

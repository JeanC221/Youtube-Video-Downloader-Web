import flet as ft

def check(name, obj):
    try:
        if hasattr(ft, name):
            val = getattr(ft, name)
            print(f"ft.{name}: EXISTS ({type(val)})")
            # Check for with_opacity if it's Colors
            if name == 'Colors' and hasattr(val, 'with_opacity'):
                 print(f"  -> ft.{name}.with_opacity: EXISTS")
        else:
            print(f"ft.{name}: MISSING")
    except Exception as e:
        print(f"ft.{name}: ERROR ({e})")

attrs = [
    'colors', 'Colors',
    'icons', 'Icons',
    'animation', 'Animation',
    'border', 'Border',
    'box_shadow', 'BoxShadow',
    'font_weight', 'FontWeight',
    'image_fit', 'ImageFit',
    'image_src', 'ImageSrc',
    'transform', 'Transform'
]

for a in attrs:
    check(a, ft)

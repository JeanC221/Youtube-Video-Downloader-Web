import flet as ft

try:
    print(f"ft.Colors.TRANSPARENT: {ft.Colors.TRANSPARENT}")
except:
    print("ft.Colors.TRANSPARENT: ERROR")

try:
    c = ft.Colors.with_opacity(0.5, "#ffffff")
    print(f"ft.Colors.with_opacity: WORKING ({c})")
except:
    print("ft.Colors.with_opacity: ERROR")

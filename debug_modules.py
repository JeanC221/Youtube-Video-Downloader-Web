import flet as ft

def check(name):
    try:
        if hasattr(ft, name):
            print(f"ft.{name}: EXISTS")
        else:
            print(f"ft.{name}: MISSING")
    except:
        print(f"ft.{name}: ERROR")

modules = ['border', 'padding', 'alignment', 'border_radius', 'margin']

for m in modules:
    check(m)

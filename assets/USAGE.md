Logo assets generated for the project. Place the desired icon files under `assets/` and reference them in packaging.

Inno Setup example (installer.iss):
  SetupIconFile=assets\concept-1-rounded-play\icon.ico

macOS bundle (Info.plist):
  CFBundleIconFile: icon.icns (place `assets/concept-1-rounded-play/icon.icns` in the app bundle Resources)

Linux desktop file (.desktop):
  Icon=/usr/share/icons/hicolor/256x256/apps/yourapp.png

Favicons: use `assets/concept-1-rounded-play/icon-16.png` / `favicon.ico` accordingly.
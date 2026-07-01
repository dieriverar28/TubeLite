#!/usr/bin/env bash
#
# Quita el acceso directo de TubeLite del menu de aplicaciones y del
# Escritorio. NO borra el codigo del proyecto ni tus preferencias
# guardadas (historial, configuracion, etc. en ~/.config/tubelite).
#
set -e

rm -f "$HOME/.local/share/applications/tubelite.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/tubelite.svg"
rm -f "$HOME/Desktop/tubelite.desktop"
rm -f "$HOME/Escritorio/tubelite.desktop"

command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "TubeLite se quito del menu de aplicaciones y del Escritorio."
echo "El codigo del proyecto y tus preferencias (~/.config/tubelite) no se borraron."

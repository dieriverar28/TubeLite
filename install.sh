#!/usr/bin/env bash
#
# Instalador de TubeLite para el usuario actual (NO hace falta sudo).
#
# Que hace:
#   1. Copia el icono a ~/.local/share/icons/hicolor/scalable/apps/
#   2. Genera un lanzador .desktop en ~/.local/share/applications/
#      (aparece en el menu de aplicaciones como cualquier otro programa)
#   3. Si existe la carpeta ~/Desktop o ~/Escritorio, deja ahi tambien
#      un acceso directo para abrir con doble clic
#   4. Da permisos de ejecucion al lanzador bin/tubelite
#
# Se puede volver a ejecutar sin problema en cualquier momento (por
# ejemplo, si la carpeta del proyecto se movio de lugar).
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$PROJECT_DIR/bin/tubelite"
ICON_SRC="$PROJECT_DIR/assets/tubelite.svg"

ICON_DEST_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/tubelite.desktop"

echo "Instalando TubeLite para $(whoami)..."
echo "Carpeta del proyecto: $PROJECT_DIR"

# ---- Verificacion basica de dependencias del sistema ----
faltantes=()
command -v python3 >/dev/null 2>&1 || faltantes+=("python3")
command -v mpv >/dev/null 2>&1 || faltantes+=("mpv")
command -v yt-dlp >/dev/null 2>&1 || faltantes+=("yt-dlp")
python3 -c "import gi; gi.require_version('Gtk', '3.0')" >/dev/null 2>&1 || faltantes+=("python3-gi / gir1.2-gtk-3.0")

if [ ${#faltantes[@]} -gt 0 ]; then
    echo ""
    echo "Aviso: no se detectaron estas dependencias en el sistema:"
    for dep in "${faltantes[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "TubeLite se va a instalar igual (el acceso directo va a"
    echo "quedar listo), pero puede no abrir hasta instalar lo que falta:"
    echo ""
    echo "  sudo apt install mpv python3-gi gir1.2-gtk-3.0"
    echo "  pip install -r requirements.txt --break-system-packages"
    echo ""
fi

chmod +x "$LAUNCHER"

# ---- Icono ----
mkdir -p "$ICON_DEST_DIR"
cp "$ICON_SRC" "$ICON_DEST_DIR/tubelite.svg"

# ---- Entrada de menu (.desktop) ----
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=TubeLite
Comment=Cliente ligero de YouTube para equipos antiguos
Exec=$LAUNCHER
Icon=tubelite
Terminal=false
Categories=AudioVideo;Player;Network;
StartupWMClass=TubeLite
EOF
chmod +x "$DESKTOP_FILE"

# Refrescar las cachés de iconos y aplicaciones, si las herramientas
# existen (no todos los sistemas las tienen instaladas, y no son
# obligatorias: sin esto, el acceso directo igual funciona, solo puede
# tardar un poco mas en aparecer en el menu)
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# ---- Acceso directo en el Escritorio (si existe la carpeta) ----
DESKTOP_FOLDER=""
if [ -d "$HOME/Desktop" ]; then
    DESKTOP_FOLDER="$HOME/Desktop"
elif [ -d "$HOME/Escritorio" ]; then
    DESKTOP_FOLDER="$HOME/Escritorio"
fi

if [ -n "$DESKTOP_FOLDER" ]; then
    cp "$DESKTOP_FILE" "$DESKTOP_FOLDER/tubelite.desktop"
    chmod +x "$DESKTOP_FOLDER/tubelite.desktop"
    # Marcar como confiable si esta disponible "gio" (evita el aviso
    # de "archivo no confiable" al hacer doble clic la primera vez en
    # entornos como GNOME o Xfce recientes)
    command -v gio >/dev/null 2>&1 && \
        gio set "$DESKTOP_FOLDER/tubelite.desktop" "metadata::trusted" true 2>/dev/null || true
fi

echo ""
echo "Listo. TubeLite deberia aparecer en el menu de aplicaciones."
if [ -n "$DESKTOP_FOLDER" ]; then
    echo "Tambien se copio un acceso directo a: $DESKTOP_FOLDER"
    echo ""
    echo "Si al hacer doble clic aparece un aviso de 'archivo no"
    echo "confiable' o 'launcher no confiable', hace clic derecho sobre"
    echo "el icono y elegi 'Permitir lanzamiento' (o 'Confiar y"
    echo "lanzar', segun el entorno de escritorio). Solo hace falta"
    echo "una vez."
fi
echo ""
echo "Para desinstalar el acceso directo (sin borrar el proyecto),"
echo "corre: ./uninstall.sh"

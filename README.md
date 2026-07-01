# TubeLite

Cliente ligero de YouTube para equipos antiguos y de bajo poder computacional.

## Objetivos

-Buscar videos en YouTube
-Reproducir en mpv (360p/480p optimizado)
-Bajo consumo de RAM y CPU
-Optimizado para Linux
-Favoritos e historial (v1.0)

## Hardware target

Diseñado para:
- Lenovo G475 (AMD E-350, 4GB RAM)
- Equipos antiguos con Linux

## Instalación

```bash
git clone https://github.com/tu-usuario/tubelite.git
cd tubelite
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 src/main.py
```

## Dependencias del sistema

```bash
sudo apt install mpv python3-gi gir1.2-gtk-3.0
```

## Instalar como aplicación de escritorio

Después de clonar el proyecto (y opcionalmente crear el entorno virtual como se indica arriba), se puede instalar un acceso directo para abrir TubeLite con doble clic, como cualquier otro programa, sin tener que escribir comandos en la terminal cada vez:

```bash
./install.sh
```

Esto agrega TubeLite al menú de aplicaciones y, si existe la carpeta `~/Desktop` (o `~/Escritorio`), deja también un acceso directo ahí. El instalador detecta automáticamente si el proyecto usa un entorno virtual (`.venv`) o el Python del sistema, así que no hace falta editar rutas a mano.

Si en algún momento se quiere quitar el acceso directo (sin borrar el proyecto ni las preferencias guardadas):

```bash
./uninstall.sh
```

## Roadmap

- [ ] v0.1 - Ventana GTK base
- [ ] v0.2 - Búsqueda con yt-dlp (sin bloqueo)
- [ ] v0.3 - Lista de resultados minimalista
- [ ] v0.4 - Reproducción en mpv
- [ ] v1.0 - Config, Favoritos, Historial

## Licencia

MIT
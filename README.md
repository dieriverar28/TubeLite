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

## Roadmap

- [ ] v0.1 - Ventana GTK base
- [ ] v0.2 - Búsqueda con yt-dlp (sin bloqueo)
- [ ] v0.3 - Lista de resultados minimalista
- [ ] v0.4 - Reproducción en mpv
- [ ] v1.0 - Config, Favoritos, Historial

## Licencia

MIT
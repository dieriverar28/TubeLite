"""
Miniaturas de video para TubeLite

Descarga las miniaturas de YouTube (120x90) en segundo plano, sin
bloquear la interfaz, y las cachea en disco para no volver a
descargarlas si ya las tenemos.

Usa el formato "default.jpg" de YouTube, que es exactamente 120x90,
asi no hace falta pedir una imagen mas grande y reescalarla.
"""

import urllib.request
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor

THUMB_WIDTH = 120
THUMB_HEIGHT = 90


class ThumbnailLoader:
    """Descarga y cachea miniaturas de video en disco, en segundo plano."""

    def __init__(self, cache_dir: Optional[Path] = None, max_workers: int = 3):
        self.cache_dir = cache_dir or (Path.home() / ".cache" / "tubelite" / "thumbnails")
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"No se pudo crear la carpeta de cache de miniaturas: {e}")

        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def _cache_path(self, video_id: str) -> Path:
        return self.cache_dir / f"{video_id}.jpg"

    def _download(self, video_id: str) -> Optional[Path]:
        """
        Descargar la miniatura de un video si todavia no esta en cache.
        Devuelve la ruta local del archivo, o None si fallo.
        """
        path = self._cache_path(video_id)
        if path.exists() and path.stat().st_size > 0:
            return path

        url = f"https://i.ytimg.com/vi/{video_id}/default.jpg"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
        except Exception:
            return None

        if not data:
            return None

        # Escribimos primero a un archivo temporal y renombramos al final,
        # para no dejar un archivo a medio escribir si algo falla en el medio
        tmp_path = path.with_suffix(".tmp")
        try:
            with open(tmp_path, "wb") as f:
                f.write(data)
            tmp_path.rename(path)
        except OSError:
            return None

        return path

    def request(self, video_id: str, on_ready: Callable):
        """
        Pedir la miniatura de un video en segundo plano.

        Cuando este lista, llama on_ready(video_id, pixbuf) usando
        GLib.idle_add, para que sea seguro actualizar widgets de GTK
        desde el resultado (GTK solo se puede tocar desde el hilo
        principal).

        Si la descarga o la conversion a imagen fallan, simplemente no
        se llama on_ready (la fila se queda con el icono de placeholder).
        """
        def _task():
            path = self._download(video_id)
            if not path:
                return
            try:
                import gi
                gi.require_version("GdkPixbuf", "2.0")
                from gi.repository import GdkPixbuf, GLib

                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(path), THUMB_WIDTH, THUMB_HEIGHT, False
                )
            except Exception:
                return
            GLib.idle_add(on_ready, video_id, pixbuf)

        self._executor.submit(_task)

    def shutdown(self):
        """Detener las descargas pendientes (llamar al cerrar la app)."""
        self._executor.shutdown(wait=False, cancel_futures=True)
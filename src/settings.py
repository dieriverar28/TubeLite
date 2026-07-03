"""
Preferencias del usuario en NitroxxTubeLite

Se guardan en disco (~/.config/tubelite/settings.json) para que la
calidad de video, el volumen, el tema y el tamaño de fuente elegidos
se mantengan entre sesiones.
"""

import json
from pathlib import Path
from typing import Optional


DEFAULTS = {
    "quality": "auto",  # "auto" (segun el hardware detectado), "480", "720" o "1080"
    "volume": 100,       # 0-150 (mpv permite pasar de 100 si hace falta)
    "dark_theme": False,
    "font_size": 10,     # tamano de fuente en puntos
    "autoplay": True,    # reproducir el siguiente resultado de la lista cuando uno termina solo
}

QUALITY_OPTIONS = ["auto", "480", "720", "1080"]
FONT_SIZE_MIN = 8
FONT_SIZE_MAX = 16


class Settings:
    """Preferencias del usuario, persistidas en disco."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or (Path.home() / ".config" / "tubelite" / "settings.json")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"No se pudo crear la carpeta de configuracion: {e}")

        self._data = self._load()

    def _load(self) -> dict:
        """Cargar la configuracion guardada, completando con los valores
        por defecto cualquier clave que falte (por ejemplo, si se agrega
        una preferencia nueva en una version futura)."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                merged = dict(DEFAULTS)
                for key in DEFAULTS:
                    if key in data:
                        merged[key] = data[key]
                return merged
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return dict(DEFAULTS)

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"No se pudo guardar la configuracion: {e}")

    def get(self, key: str):
        """Obtener una preferencia (o su valor por defecto si no existe)."""
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value):
        """Cambiar una preferencia y guardarla en disco de inmediato."""
        if key not in DEFAULTS:
            return
        self._data[key] = value
        self._save()

    def get_ytdl_format(self) -> str:
        """
        Construir el string de formato de yt-dlp segun la calidad elegida.
        Si esta en "auto", se usa la deteccion automatica de hardware que
        ya hace config.py (recomendado para el Lenovo G475).
        """
        quality = self.get("quality")
        if not quality or quality == "auto":
            from config import Config
            return Config.YTDL_FORMAT
        return f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

    def reset_to_defaults(self):
        """Restaurar todas las preferencias a los valores por defecto."""
        self._data = dict(DEFAULTS)
        self._save()


# Instancia compartida por toda la aplicacion (gui.py y player.py leen
# y escriben las mismas preferencias, sin tener que pasarse el objeto
# de un lado a otro).
_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Devolver la instancia compartida de Settings (patron singleton simple)."""
    global _instance
    if _instance is None:
        _instance = Settings()
    return _instance
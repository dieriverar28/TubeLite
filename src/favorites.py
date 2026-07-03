"""
Favoritos de TubeLite

Guarda videos para volver a reproducirlos directamente, sin tener que
buscarlos de nuevo. Se persisten en disco (~/.config/tubelite/favorites.json)
junto con los datos necesarios para mostrarlos (titulo, canal,
duracion, etc.) y su URL directa. Las miniaturas no se guardan aparte:
se reutiliza la cache de thumbnails.py, que ya cachea por id de video
sin importar de que busqueda haya salido.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


class Favorites:
    """Lista de videos favoritos, persistida en disco."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or (Path.home() / ".config" / "tubelite" / "favorites.json")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"No se pudo crear la carpeta de favoritos: {e}")

        self._items: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict) and item.get("id")]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return []

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._items, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"No se pudo guardar los favoritos: {e}")

    def is_favorite(self, video_id: str) -> bool:
        """Saber si un video ya esta en favoritos."""
        if not video_id:
            return False
        return any(item.get("id") == video_id for item in self._items)

    def add(self, video: Dict):
        """Agregar un video a favoritos (al principio de la lista). Si
        ya estaba, no se duplica."""
        video_id = video.get("id")
        if not video_id or self.is_favorite(video_id):
            return

        # Guardamos solo los campos necesarios para mostrarlo y
        # reproducirlo despues, sin depender de una nueva busqueda
        entry = {
            "id": video_id,
            "title": video.get("title", "Sin titulo"),
            "url": video.get("url", ""),
            "uploader": video.get("uploader", "Desconocido"),
            "duration": video.get("duration", 0),
            "view_count": video.get("view_count", 0),
        }
        self._items.insert(0, entry)
        self._save()

    def remove(self, video_id: str):
        """Quitar un video de favoritos por su id."""
        before = len(self._items)
        self._items = [item for item in self._items if item.get("id") != video_id]
        if len(self._items) != before:
            self._save()

    def toggle(self, video: Dict) -> bool:
        """Agregar o quitar de favoritos segun corresponda. Devuelve
        True si quedo agregado, False si quedo quitado (o si el video
        no tenia id valido)."""
        video_id = video.get("id")
        if not video_id:
            return False
        if self.is_favorite(video_id):
            self.remove(video_id)
            return False
        self.add(video)
        return True

    def get_all(self) -> List[Dict]:
        """Devolver todos los favoritos, del agregado mas reciente al mas antiguo."""
        return list(self._items)


# Instancia compartida por toda la aplicacion (mismo patron que
# settings.py y su get_settings()).
_instance: Optional[Favorites] = None


def get_favorites() -> Favorites:
    """Devolver la instancia compartida de Favorites."""
    global _instance
    if _instance is None:
        _instance = Favorites()
    return _instance

"""
Historial de busquedas de TubeLite

Guarda las ultimas MAX_ITEMS busquedas en un archivo JSON, para que
el historial sobreviva a que se cierre y abra la aplicacion.

Ubicacion por defecto: ~/.config/tubelite/history.json
"""

import json
from pathlib import Path
from typing import List, Optional


class SearchHistory:
    """Historial de busquedas recientes, persistido en disco."""

    MAX_ITEMS = 10

    def __init__(self, path: Optional[Path] = None):
        self.path = path or (Path.home() / ".config" / "tubelite" / "history.json")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"No se pudo crear la carpeta de historial: {e}")

        self._items: List[str] = self._load()

    def _load(self) -> List[str]:
        """Cargar el historial guardado en disco, si existe."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [str(item) for item in data][: self.MAX_ITEMS]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return []

    def _save(self):
        """Guardar el historial actual en disco."""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._items, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"No se pudo guardar el historial: {e}")

    def add(self, query: str):
        """
        Agregar una busqueda al historial. Si ya existia (sin importar
        mayusculas/minusculas), se mueve al principio en vez de duplicarse.
        Se mantienen solo las MAX_ITEMS mas recientes.
        """
        query = query.strip()
        if not query:
            return

        self._items = [q for q in self._items if q.lower() != query.lower()]
        self._items.insert(0, query)
        self._items = self._items[: self.MAX_ITEMS]
        self._save()

    def get_all(self) -> List[str]:
        """Devolver el historial completo, del mas reciente al mas antiguo."""
        return list(self._items)

    def clear(self):
        """Vaciar el historial."""
        self._items = []
        self._save()

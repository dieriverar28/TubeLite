"""
Modulo de busqueda en YouTube usando yt-dlp
Diseñado para ser ligero, rapido y sin bloquear la UI

v0.4 - Busqueda en DOS FASES:
  1) Fase rapida (--flat-playlist): trae la lista basica en 1-3 seg,
     sin resolver cada video individualmente.
  2) Fase de enriquecido (en paralelo, en segundo plano): completa
     duracion / vistas / canal SOLO si faltan, sin bloquear la lista
     ya visible.

Ademas incluye una cache simple en memoria para no repetir la misma
busqueda dos veces en la misma sesion.
"""

import subprocess
import json
from typing import List, Dict, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class YouTubeSearcher:
    """Busqueda en YouTube usando yt-dlp"""

    def __init__(self):
        """Inicializar el buscador"""
        self.yt_dlp_path = "yt-dlp"
        # Cache simple en memoria: {"query::max_results": [videos]}
        # Vive solo mientras la app esta abierta (no se guarda en disco).
        self._cache: Dict[str, List[Dict]] = {}

    # ------------------------------------------------------------------
    # FASE 1: busqueda rapida
    # ------------------------------------------------------------------
    def search_fast(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Busqueda RAPIDA usando --flat-playlist.

        No resuelve cada video por separado, solo lee la pagina de
        resultados de busqueda. Esto es MUCHO mas rapido (1-3 seg en
        vez de 10-30+ seg) pero a veces no trae duracion o vistas
        exactas; eso se completa despues con enrich_all().

        Args:
            query: Termino de busqueda
            max_results: Numero maximo de resultados

        Returns:
            Lista de diccionarios con los resultados (puede tener
            duration=0 o view_count=0 si yt-dlp no los trajo en esta fase)
        """
        query = query.strip()
        if not query:
            return []

        cache_key = f"{query.lower()}::{max_results}"
        if cache_key in self._cache:
            # Devolvemos una copia para que la UI no mute la cache
            return [dict(v) for v in self._cache[cache_key]]

        cmd = [
            self.yt_dlp_path,
            f"ytsearch{max_results}:{query}",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
            "--skip-download",
            "-q",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except subprocess.TimeoutExpired:
            print("Busqueda rapida expirada (timeout)")
            return []
        except FileNotFoundError:
            print("yt-dlp no esta instalado o no esta en el PATH")
            return []
        except Exception as e:
            print(f"Error en busqueda rapida: {e}")
            return []

        if result.returncode != 0:
            return []

        videos = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            video_id = entry.get("id", "")
            videos.append({
                "id": video_id,
                "title": entry.get("title", "Sin titulo"),
                "duration": entry.get("duration") or 0,
                "url": entry.get("url")
                    or entry.get("webpage_url")
                    or (f"https://www.youtube.com/watch?v={video_id}" if video_id else ""),
                "uploader": entry.get("uploader") or entry.get("channel") or "Desconocido",
                "view_count": entry.get("view_count") or 0,
            })

        if videos:
            self._cache[cache_key] = [dict(v) for v in videos]

        return videos

    # ------------------------------------------------------------------
    # FASE 2: enriquecido en paralelo (duracion / vistas que falten)
    # ------------------------------------------------------------------
    def enrich_video(self, video_id: str) -> Optional[Dict]:
        """
        Obtiene metadata completa de UN solo video (duracion real,
        vistas reales, canal). Se usa en paralelo desde enrich_all().
        """
        if not video_id:
            return None

        cmd = [
            self.yt_dlp_path,
            f"https://www.youtube.com/watch?v={video_id}",
            "--dump-json",
            "--no-warnings",
            "--skip-download",
            "-q",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=12,
            )
        except Exception:
            return None

        if result.returncode != 0 or not result.stdout.strip():
            return None

        try:
            entry = json.loads(result.stdout.strip().splitlines()[0])
        except (json.JSONDecodeError, IndexError):
            return None

        return {
            "id": video_id,
            "duration": entry.get("duration") or 0,
            "view_count": entry.get("view_count") or 0,
            "uploader": entry.get("uploader") or entry.get("channel") or "Desconocido",
        }

    def enrich_all(
        self,
        videos: List[Dict],
        on_video_ready: Callable[[Dict], None],
        max_workers: int = 4,
        only_missing: bool = True,
    ):
        """
        Completa datos faltantes (duracion / vistas) de varios videos
        EN PARALELO. Llama on_video_ready(video_actualizado) apenas
        cada uno este listo, para que la UI se actualice de a poco
        (streaming) en vez de esperar a que todos terminen.

        Pensado para correr en un thread de background, NO en el
        hilo principal de GTK.

        Args:
            videos: lista de videos ya mostrados (de search_fast)
            on_video_ready: callback(video) llamado por cada video
                            que se termina de enriquecer
            max_workers: cuantas resoluciones en paralelo (4 es un
                         buen numero para no saturar un notebook viejo)
            only_missing: si True, solo enriquece los que no traen
                          duracion o vistas (ahorra llamadas a yt-dlp)
        """
        pending = [
            v for v in videos
            if v.get("id") and (not only_missing or not v.get("duration") or not v.get("view_count"))
        ]
        if not pending:
            return

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_video = {
                executor.submit(self.enrich_video, v["id"]): v for v in pending
            }
            for future in as_completed(future_to_video):
                video = future_to_video[future]
                try:
                    data = future.result()
                except Exception:
                    continue
                if data:
                    video.update(data)
                    on_video_ready(video)

    # ------------------------------------------------------------------
    # Compatibilidad hacia atras: search() = fase rapida + enriquecido
    # bloqueante (por si algo mas del proyecto todavia la usa asi)
    # ------------------------------------------------------------------
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Busqueda "todo en uno" (bloqueante). Se mantiene por
        compatibilidad, pero para la UI conviene usar search_fast()
        + enrich_all() para que los resultados aparezcan progresivamente.
        """
        videos = self.search_fast(query, max_results=max_results)
        if not videos:
            return []
        self.enrich_all(videos, on_video_ready=lambda v: None, only_missing=True)
        return videos

    # ------------------------------------------------------------------
    # Utilidades de formato
    # ------------------------------------------------------------------
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Formatear duracion en segundos a HH:MM:SS"""
        if not seconds:
            return "--:--"

        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"

    @staticmethod
    def format_views(count: int) -> str:
        """Formatear numero de visualizaciones"""
        if not count:
            return "--"
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K"
        else:
            return str(count)
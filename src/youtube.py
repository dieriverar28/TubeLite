"""
Módulo de búsqueda en YouTube usando yt-dlp
Diseñado para ser ligero y sin bloquear la UI
"""

import subprocess
import json
import re
from typing import List, Dict, Optional


class YouTubeSearcher:
    """Búsqueda en YouTube usando yt-dlp"""
    
    def __init__(self):
        """Inicializar el buscador"""
        self.yt_dlp_path = "yt-dlp"
    
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Buscar videos en YouTube
        
        Args:
            query: Término de búsqueda
            max_results: Número máximo de resultados
            
        Returns:
            Lista de diccionarios con los resultados
        """
        try:
            # Comando de yt-dlp para buscar
            cmd = [
                self.yt_dlp_path,
                f"ytsearch{max_results}:{query}",
                "--dump-json",
                "--no-warnings",
                "-q"
            ]
            
            # Ejecutar búsqueda
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                return []
            
            # Parsear JSON
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return []
            
            # Extraer información de los videos
            videos = []
            if "entries" in data:
                for entry in data["entries"]:
                    video = {
                        "id": entry.get("id", ""),
                        "title": entry.get("title", "Sin título"),
                        "duration": entry.get("duration", 0),
                        "url": entry.get("url", ""),
                        "uploader": entry.get("uploader", "Desconocido"),
                        "view_count": entry.get("view_count", 0)
                    }
                    videos.append(video)
            
            return videos
        
        except subprocess.TimeoutExpired:
            print("Búsqueda expirada (timeout)")
            return []
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            return []
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Formatear duración en segundos a HH:MM:SS"""
        if not seconds:
            return "--:--"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    @staticmethod
    def format_views(count: int) -> str:
        """Formatear número de visualizaciones"""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K"
        else:
            return str(count)
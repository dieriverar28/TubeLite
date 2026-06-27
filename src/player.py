"""
Reproductor de video usando mpv
Optimizado para hardware antiguo (AMD E-350)
Con sincronización audio/video mejorada
"""

import subprocess
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Player:
    """Control del reproductor mpv optimizado"""

    @staticmethod
    def play(url: str, title: str = ""):
        """
        Reproducir un video de YouTube con mpv
        Optimizado para baja latencia en hardware antiguo
        
        Args:
            url: URL del video
            title: Título del video (opcional)
        """
        try:
            # Construir comando con opciones de Config
            cmd = ["mpv"]
            
            # Agregar opciones base
            cmd.extend(Config.MPV_OPTS)
            
            # Formato de video para baja latencia
            ytdl_format = f"{Config.VIDEO_QUALITY}+{Config.AUDIO_QUALITY}/best"
            cmd.append(f"--ytdl-format={ytdl_format}")
            
            # Agregar URL
            cmd.append(url)
            
            logger.info(f"▶Reproduciendo: {title or url}")
            logger.debug(f"Comando: {' '.join(cmd)}")
            
            # Popen no bloquea la interfaz GTK
            subprocess.Popen(cmd)
        
        except FileNotFoundError:
            logger.error("mpv no está instalado")
            logger.error("Instala con: sudo apt install mpv")
        except Exception as e:
            logger.error(f"Error al reproducir: {e}")
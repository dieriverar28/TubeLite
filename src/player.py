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
            # Construir comando partiendo desde la base "mpv"
            cmd = ["mpv"]
            
            # Agrega directamente todas las opciones optimizadas de config.py
            # (Esto ya incluye el --vo=gpu, --hwdec=vaapi y el --ytdl-format dinámico)
            cmd.extend(Config.MPV_OPTS)
            
            # Agregar la URL al final de los argumentos
            cmd.append(url)
            
            logger.info(f"▶ Reproduciendo: {title or url}")
            # Cambiado a info para que puedas verificar el comando exacto en la terminal
            logger.info(f"Comando ejecutado: {' '.join(cmd)}")
            
            # Popen no bloquea la interfaz GTK
            subprocess.Popen(cmd)
        
        except FileNotFoundError:
            logger.error("mpv no está instalado")
            logger.error("Instala con: sudo apt install mpv")
        except Exception as e:
            logger.error(f"Error al reproducir: {e}")
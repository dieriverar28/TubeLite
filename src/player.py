"""
Reproductor de video usando mpv
Optimizado para hardware antiguo (AMD E-350)
Con sincronizacion audio/video mejorada

v0.4 - Ademas detecta y reintenta automaticamente dos fallos comunes:
  - Fallo de DNS momentaneo (Failed to resolve hostname) -> reintenta
    una vez despues de una breve pausa.
  - Bloqueo anti-bot de YouTube (Sign in to confirm you're not a bot)
    -> reintenta una vez usando cookies del navegador, SI
    Config.COOKIES_FROM_BROWSER esta configurado.
"""

import subprocess
import logging
import threading
import time
from config import Config
from settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cuanto tiempo (segundos) esperamos tras lanzar mpv para decidir si
# "arranco bien" o "fallo rapido". Si mpv sigue vivo pasado este tiempo,
# asumimos que esta reproduciendo con normalidad.
FAIL_DETECTION_WINDOW = 8.0


class Player:
    """Control del reproductor mpv optimizado, con reintento automatico"""

    @staticmethod
    def _build_cmd(url: str, use_cookies: bool = False, fallback_vo: bool = False) -> list:
        """Arma el comando de mpv. La calidad y el volumen se leen de
        las preferencias guardadas (settings.py) en cada llamada, para
        que un cambio en la pantalla de Configuracion aplique de
        inmediato sin reiniciar TubeLite. Si use_cookies=True, agrega
        las cookies del navegador configurado (para sortear el
        bloqueo anti-bot)."""
        settings = get_settings()

        cmd = ["mpv"]
        cmd.extend(Config.MPV_OPTS)
        cmd.append(f"--ytdl-format={settings.get_ytdl_format()}")
        cmd.append(f"--volume={settings.get('volume')}")
        
        if fallback_vo:
            cmd.append("--vo=x11")
            cmd.append("--hwdec=no")

        if use_cookies and Config.COOKIES_FROM_BROWSER:
            cmd.append(
                f"--ytdl-raw-options=cookies-from-browser={Config.COOKIES_FROM_BROWSER}"
            )

        cmd.append(url)
        return cmd

    @staticmethod
    def _run_once(cmd: list):
        """
        Lanza mpv y monitorea su salida durante los primeros segundos
        para detectar errores tempranos conocidos (DNS, bot-check).

        Devuelve (proceso, estado) donde estado es:
          "ok"    -> mpv sigue vivo pasado el tiempo de deteccion (bien)
          "dns"   -> fallo por DNS momentaneo
          "bot"   -> fallo por bloqueo anti-bot de YouTube
          "other" -> fallo rapido por otro motivo no identificado
        """
        logger.info(f"Comando ejecutado: {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        detected = {"value": None}

        def _watch_stderr():
            # Vamos leyendo la salida de mpv linea por linea. La re-imprimimos
            # tal cual para no perder visibilidad en la terminal (igual que antes),
            # y de paso buscamos patrones de error conocidos.
            try:
                for line in proc.stderr:
                    print(line, end="")
                    if ("Failed to resolve hostname" in line
                            or "Temporary failure in name resolution" in line):
                        detected["value"] = "dns"
                    elif "Sign in to confirm" in line or "not a bot" in line:
                        detected["value"] = "bot"
                    elif ("No 3D enabled" in line
                            or "DRI3 error" in line
                            or "Could not get DRI3" in line):
                        detected["value"] = "vo"
            except Exception:
                pass

        reader = threading.Thread(target=_watch_stderr, daemon=True)
        reader.start()

        start = time.time()
        while time.time() - start < FAIL_DETECTION_WINDOW:
            if proc.poll() is not None:
                # mpv ya termino (fallo rapido). Le damos un instante al
                # hilo lector para que termine de procesar el stderr
                # pendiente, si no la clasificacion del error puede
                # perderse por una condicion de carrera.
                reader.join(timeout=1.0)
                return proc, (detected["value"] or "other")
            time.sleep(0.3)

        # Sigue vivo pasado el tiempo de deteccion -> lo damos por bueno
        return proc, "ok"

    @staticmethod
    def play(url: str, title: str = ""):
        """
        Reproducir un video de YouTube con mpv.
        Optimizado para baja latencia en hardware antiguo, con
        reintento automatico ante fallos transitorios conocidos.

        Args:
            url: URL del video
            title: Titulo del video (opcional)
        """
        try:
            logger.info(f"Reproduciendo: {title or url}")

            # Intento 1: normal, sin cookies
            cmd = Player._build_cmd(url, use_cookies=False)
            proc, status = Player._run_once(cmd)

            if status == "ok":
                return

            if status == "dns":
                logger.warning(
                    "Fallo de DNS momentaneo al resolver el servidor de video. "
                    "Reintentando en 2 segundos..."
                )
                time.sleep(2)
                cmd = Player._build_cmd(url, use_cookies=False)
                proc, status = Player._run_once(cmd)
                if status == "ok":
                    return
                logger.error(
                    "Sigue fallando tras el reintento. Puede ser un problema "
                    "de red/DNS mas persistente (revisa tu conexion)."
                )
                return

            if status == "bot":
                if Config.COOKIES_FROM_BROWSER:
                    logger.warning(
                        "YouTube esta pidiendo verificacion anti-bot para este "
                        f"video. Reintentando con las cookies de {Config.COOKIES_FROM_BROWSER}..."
                    )
                    cmd = Player._build_cmd(url, use_cookies=True)
                    proc, status = Player._run_once(cmd)
                    if status == "ok":
                        return
                    logger.error(
                        "YouTube sigue pidiendo verificacion incluso con cookies. "
                        f"Revisa que tengas sesion iniciada en YouTube con {Config.COOKIES_FROM_BROWSER} "
                        "y que ese navegador este cerrado (algunos navegadores bloquean "
                        "el acceso a las cookies mientras estan abiertos)."
                    )
                else:
                    logger.error(
                        "YouTube esta pidiendo verificacion anti-bot para este video. "
                        "Configura Config.COOKIES_FROM_BROWSER (ej: 'firefox') en "
                        "config.py para que TubeLite use tu sesion ya logueada del "
                        "navegador y evite este bloqueo."
                    )
                return
            if status == "vo":
                logger.warning(
                    "No se pudo inicializar la salida de video por GPU "
                    "(comun en maquinas virtuales sin aceleracion 3D "
                    "habilitada). Reintentando con salida de video "
                    "basica, sin aceleracion por hardware..."
                )
                cmd = Player._build_cmd(url, use_cookies=False, fallback_vo=True)
                proc, status = Player._run_once(cmd)
                if status == "ok":
                    return
                logger.error(
                    "Sigue sin poder reproducir incluso con salida de video "
                    "basica. Si esta en una maquina virtual (VirtualBox, "
                    "VMware), active la aceleracion 3D en la configuracion "
                    "de Pantalla de la VM e instale las Guest Additions. "
                    "Si esto es hardware real, revise que los drivers de "
                    "video esten bien instalados."
                )
                return
            logger.error(
                f"mpv no pudo reproducir '{title or url}' (motivo no identificado, "
                "revisa el log de arriba para mas detalle)."
            )

        except FileNotFoundError:
            logger.error("mpv no esta instalado")
            logger.error("Instala con: sudo apt install mpv")
        except Exception as e:
            logger.error(f"Error al reproducir: {e}")
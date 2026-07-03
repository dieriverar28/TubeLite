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
from typing import Optional, Callable
from config import Config
from settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cuanto tiempo (segundos) esperamos tras lanzar mpv para decidir si
# "arranco bien" o "fallo rapido". Si mpv sigue vivo pasado este tiempo,
# asumimos que esta reproduciendo con normalidad.
FAIL_DETECTION_WINDOW = 8.0

class _RunResult:
    """Resultado de lanzar mpv una vez: el proceso, el estado inicial
    detectado, y las referencias necesarias para poder seguir
    monitoreando la salida hasta que el proceso termine de verdad."""

    __slots__ = ("proc", "status", "detected", "reader")

    def __init__(self, proc, status: str, detected: dict, reader: threading.Thread):
        self.proc = proc
        self.status = status
        self.detected = detected
        self.reader = reader
class Player:
    """Control del reproductor mpv optimizado, con reintento automatico"""

    @staticmethod
    def _classify_exit_line(line: str) -> Optional[str]:
        """Traducir la linea final de mpv a un motivo estable."""
        if not line.startswith("Exiting..."):
            return None

        normalized = line.lower()
        if ("end of file" in normalized
                or "eof reached" in normalized
                or "eof" in normalized):
            return "eof"
        if "quit" in normalized:
            return "quit"
        return "error"

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
    def _run_once(cmd: list) -> "_RunResult":
        """
        Lanza mpv y monitorea su salida. El hilo lector sigue
        funcionando despues de que esta funcion retorna, asi se puede
        usar mas adelante para saber como termino la reproduccion.

        El "status" del resultado puede ser:
          "ok"    -> mpv esta reproduciendo bien
          "dns"   -> fallo por DNS momentaneo
          "bot"   -> fallo por bloqueo anti-bot de YouTube
          "vo"    -> fallo por falta de aceleracion 3D/GPU (comun en VMs)
          "other" -> fallo por otro motivo no identificado
        """
        logger.info(f"Comando ejecutado: {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # "value" es el motivo de un fallo TEMPRANO. "exit_reason" es
        # como termino la reproduccion en definitiva: "eof" (llego al
        # final solo), "quit" (el usuario cerro mpv) o "error" (fallo
        # durante la reproduccion, no al inicio).
        detected = {"value": None, "exit_reason": None}

        def _watch_stderr():
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

                    exit_reason = Player._classify_exit_line(line)
                    if exit_reason:
                        detected["exit_reason"] = exit_reason
            except Exception:
                pass

        reader = threading.Thread(target=_watch_stderr, daemon=True)
        reader.start()

        start = time.time()
        while time.time() - start < FAIL_DETECTION_WINDOW:
            if proc.poll() is not None:
                reader.join(timeout=1.0)

                # Un cierre TEMPRANO no siempre es un fallo: un video
                # muy corto puede terminar solo (eof) o el usuario
                # puede cerrarlo (quit) antes de la ventana de deteccion.
                if detected["value"]:
                    return _RunResult(proc, detected["value"], detected, reader)
                if detected["exit_reason"] in ("eof", "quit"):
                    return _RunResult(proc, "ok", detected, reader)
                return _RunResult(proc, "other", detected, reader)
            time.sleep(0.3)

        return _RunResult(proc, "ok", detected, reader)

    @staticmethod
    def _wait_and_get_exit_reason(result: "_RunResult") -> Optional[str]:
        """Esperar a que mpv termine de verdad y devolver el motivo
        ("eof", "quit", "error" o None si no se pudo determinar)."""
        result.proc.wait()
        result.reader.join(timeout=1.0)
        return result.detected.get("exit_reason")

    @staticmethod
    def _attempt_playback(url: str, title: str) -> Optional["_RunResult"]:
        """
        Intenta reproducir con todos los reintentos conocidos (DNS,
        bloqueo anti-bot, falta de GPU). Devuelve el _RunResult que
        funciono, o None si ningun intento funciono.
        """
        logger.info(f"Reproduciendo: {title or url}")

        result = Player._run_once(Player._build_cmd(url, use_cookies=False))
        if result.status == "ok":
            return result

        if result.status == "dns":
            logger.warning(
                "Fallo de DNS momentaneo al resolver el servidor de video. "
                "Reintentando en 2 segundos..."
            )
            time.sleep(2)
            result = Player._run_once(Player._build_cmd(url, use_cookies=False))
            if result.status == "ok":
                return result
            logger.error(
                "Sigue fallando tras el reintento. Puede ser un problema "
                "de red/DNS mas persistente (revisa tu conexion)."
            )
            return None

        if result.status == "bot":
            if Config.COOKIES_FROM_BROWSER:
                logger.warning(
                    "YouTube esta pidiendo verificacion anti-bot para este "
                    f"video. Reintentando con las cookies de {Config.COOKIES_FROM_BROWSER}..."
                )
                result = Player._run_once(Player._build_cmd(url, use_cookies=True))
                if result.status == "ok":
                    return result
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
            return None

        if result.status == "vo":
            logger.warning(
                "No se pudo inicializar la salida de video por GPU "
                "(comun en maquinas virtuales sin aceleracion 3D "
                "habilitada). Reintentando con salida de video "
                "basica, sin aceleracion por hardware..."
            )
            result = Player._run_once(
                Player._build_cmd(url, use_cookies=False, fallback_vo=True)
            )
            if result.status == "ok":
                return result
            logger.error(
                "Sigue sin poder reproducir incluso con salida de video "
                "basica. Si esta en una maquina virtual (VirtualBox, "
                "VMware), active la aceleracion 3D en la configuracion "
                "de Pantalla de la VM e instale las Guest Additions. "
                "Si esto es hardware real, revise que los drivers de "
                "video esten bien instalados."
            )
            return None

        logger.error(
            f"mpv no pudo reproducir '{title or url}' (motivo no identificado, "
            "revise el log de arriba para mas detalle)."
        )
        return None

    @staticmethod
    def play(url: str, title: str = "", on_finished: Optional[Callable[[Optional[str]], None]] = None):
        """
        Reproducir un video de YouTube con mpv.

        Args:
            url: URL del video
            title: Titulo del video (opcional)
            on_finished: callback opcional, llamado UNA SOLA VEZ cuando
                mpv termina. Recibe "eof" (termino solo), "quit" (el
                usuario lo cerro), "error" (fallo durante la
                reproduccion), o None (nunca llego a reproducir).
                Se ejecuta en un hilo secundario: si toca widgets de
                GTK, debe usar GLib.idle_add.
        """
        reason: Optional[str] = None
        try:
            result = Player._attempt_playback(url, title)
            if result is not None:
                reason = Player._wait_and_get_exit_reason(result)
        except FileNotFoundError:
            logger.error("mpv no esta instalado")
            logger.error("Instale con: sudo apt install mpv")
        except Exception as e:
            logger.error(f"Error al reproducir: {e}")
        finally:
            if on_finished:
                on_finished(reason)

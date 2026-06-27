import subprocess


class Player:

    @staticmethod
    def play(url: str):
        cmd = [
            "mpv",
            "--ytdl=yes",
            "--profile=low-latency",
            "--ytdl-format=bestvideo[height<=360]+bestaudio/best[height<=360]",
            url,
        ]

        subprocess.Popen(cmd)
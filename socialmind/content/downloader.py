from __future__ import annotations

import os

import ffmpeg
import yt_dlp

_MEDIA_TMP = "media_tmp"


class ContentDownloader:
    """Download reference content for research or remixing."""

    @staticmethod
    async def download_youtube(url: str, format: str = "mp4") -> str:
        """Download a YouTube video and return the local file path."""
        os.makedirs(_MEDIA_TMP, exist_ok=True)
        output_template = os.path.join(_MEDIA_TMP, "yt_%(id)s.%(ext)s")
        ydl_opts = {
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "cookiefile": None,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    @staticmethod
    async def extract_audio(video_path: str) -> str:
        """Extract audio track from a video file as MP3."""
        audio_path = video_path.replace(".mp4", ".mp3")
        (
            ffmpeg.input(video_path)
            .output(audio_path, acodec="libmp3lame", ab="192k")
            .overwrite_output()
            .run(quiet=True)
        )
        return audio_path


from __future__ import annotations

import os
from uuid import uuid4

_MEDIA_TMP = "media_tmp"

_PLATFORM_SPECS: dict[str, dict[str, object]] = {
    "instagram_reel": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "bitrate": "4M",
        "max_seconds": 90,
    },
    "tiktok": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "bitrate": "4M",
        "max_seconds": 180,
    },
    "youtube_short": {
        "width": 1080,
        "height": 1920,
        "fps": 60,
        "bitrate": "8M",
        "max_seconds": 60,
    },
    "twitter": {
        "width": 1280,
        "height": 720,
        "fps": 30,
        "bitrate": "2M",
        "max_seconds": 140,
    },
    "linkedin": {
        "width": 1280,
        "height": 720,
        "fps": 30,
        "bitrate": "5M",
        "max_seconds": 600,
    },
}


def _require_ffmpeg():
    try:
        import ffmpeg
    except ImportError as exc:
        raise RuntimeError(
            "ffmpeg-python is not installed. Install the 'media' extra to use video processing features."
        ) from exc
    return ffmpeg


def _require_moviepy():
    try:
        from moviepy.editor import CompositeVideoClip, TextClip, VideoFileClip
    except ImportError as exc:
        raise RuntimeError(
            "moviepy is not installed. Install the 'media' extra to use captioning and slideshow features."
        ) from exc
    return CompositeVideoClip, TextClip, VideoFileClip


class VideoProcessor:
    @staticmethod
    async def transcode_for_platform(input_path: str, platform: str) -> str:
        """Transcode video to the platform-required specs."""
        ffmpeg = _require_ffmpeg()
        spec = _PLATFORM_SPECS[platform]
        output_path = f"{input_path}_transcoded.mp4"

        (
            ffmpeg.input(input_path, ss=0, t=spec["max_seconds"])
            .filter(
                "scale",
                spec["width"],
                spec["height"],
                force_original_aspect_ratio="decrease",
            )
            .filter("pad", spec["width"], spec["height"], "(ow-iw)/2", "(oh-ih)/2")
            .output(
                output_path,
                vcodec="libx264",
                acodec="aac",
                video_bitrate=spec["bitrate"],
                r=spec["fps"],
                preset="fast",
                movflags="+faststart",
            )
            .overwrite_output()
            .run(quiet=True)
        )
        return output_path

    @staticmethod
    async def add_captions(video_path: str, captions: list[dict[str, object]]) -> str:
        """Add timed text captions to a video."""
        composite_video_clip, text_clip, video_file_clip = _require_moviepy()
        clip = video_file_clip(video_path)
        text_clips = []
        for caption in captions:
            txt = (
                text_clip(
                    str(caption["text"]),
                    fontsize=50,
                    color="white",
                    stroke_color="black",
                    stroke_width=2,
                )
                .set_position(("center", "bottom"))
                .set_start(caption["start"])
                .set_end(caption["end"])
            )
            text_clips.append(txt)

        final = composite_video_clip([clip] + text_clips)
        output_path = video_path.replace(".mp4", "_captioned.mp4")
        final.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
        return output_path

    @staticmethod
    async def create_slideshow(
        image_paths: list[str],
        duration_per_image: float = 3.0,
        audio_path: str | None = None,
    ) -> str:
        """Create a video slideshow from multiple images."""
        ffmpeg = _require_ffmpeg()
        os.makedirs(_MEDIA_TMP, exist_ok=True)
        output_path = os.path.join(_MEDIA_TMP, f"slideshow_{uuid4()}.mp4")
        total_duration = len(image_paths) * duration_per_image

        inputs = [ffmpeg.input(img, loop=1, t=duration_per_image) for img in image_paths]
        joined = ffmpeg.concat(*inputs, v=1, a=0).node
        stream = joined[0]

        if audio_path:
            audio = ffmpeg.input(audio_path, t=total_duration)
            out = ffmpeg.output(stream, audio.audio, output_path, vcodec="libx264", acodec="aac")
        else:
            out = ffmpeg.output(stream, output_path, vcodec="libx264")

        out.overwrite_output().run(quiet=True)
        return output_path

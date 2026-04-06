from __future__ import annotations

import os
from uuid import uuid4

import ffmpeg
from moviepy.editor import CompositeVideoClip, TextClip, VideoFileClip

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
}


class VideoProcessor:
    @staticmethod
    async def transcode_for_platform(input_path: str, platform: str) -> str:
        """Transcode video to the platform-required specs."""
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
    async def add_captions(
        video_path: str, captions: list[dict[str, object]]
    ) -> str:
        """Add timed text captions to a video."""
        clip = VideoFileClip(video_path)
        text_clips = []
        for caption in captions:
            txt = (
                TextClip(
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

        final = CompositeVideoClip([clip] + text_clips)
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
        os.makedirs(_MEDIA_TMP, exist_ok=True)
        output_path = os.path.join(_MEDIA_TMP, f"slideshow_{uuid4()}.mp4")
        total_duration = len(image_paths) * duration_per_image

        inputs = [ffmpeg.input(img, loop=1, t=duration_per_image) for img in image_paths]
        joined = ffmpeg.concat(*inputs, v=1, a=0).node
        stream = joined[0]

        if audio_path:
            audio = ffmpeg.input(audio_path, t=total_duration)
            out = ffmpeg.output(
                stream, audio.audio, output_path, vcodec="libx264", acodec="aac"
            )
        else:
            out = ffmpeg.output(stream, output_path, vcodec="libx264")

        out.overwrite_output().run(quiet=True)
        return output_path


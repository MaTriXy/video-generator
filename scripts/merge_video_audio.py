import argparse
import subprocess
import sys
from pathlib import Path


def validate_file_exists(file_path: str, file_type: str) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{file_type} file not found: {file_path}")
    return path


def validate_file_extension(file_path: Path, expected_ext: str, file_type: str) -> None:
    if file_path.suffix.lower() != expected_ext.lower():
        raise ValueError(f"{file_type} file must have {expected_ext} extension, got: {file_path.suffix}")


def generate_output_path(video_path: Path, suffix: str = "_merged") -> Path:
    return video_path.parent / f"{video_path.stem}{suffix}.mp4"


def ms_to_seconds(ms: int) -> float:
    return ms / 1000.0


def build_crop_filter(left: int, top: int, right: int, bottom: int) -> str:
    return f"crop=iw-{left}-{right}:ih-{top}-{bottom}:{left}:{top}"


def merge_video_audio(
    video_path: str,
    audio_path: str,
    output_path: str = None,
    audio_delay_ms: int = 10000,
    crop_left: int = 0,
    crop_top: int = 0,
    crop_right: int = 0,
    crop_bottom: int = 0
) -> Path:
    video = validate_file_exists(video_path, "Video")
    audio = validate_file_exists(audio_path, "Audio")

    validate_file_extension(video, ".mp4", "Video")
    validate_file_extension(audio, ".mp3", "Audio")

    if output_path:
        output = Path(output_path)
    else:
        output = generate_output_path(video)

    output.parent.mkdir(parents=True, exist_ok=True)

    delay_seconds = ms_to_seconds(audio_delay_ms)
    has_crop = any([crop_left, crop_top, crop_right, crop_bottom])

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(delay_seconds),
        "-i", str(video),
        "-i", str(audio),
    ]

    if has_crop:
        crop_filter = build_crop_filter(crop_left, crop_top, crop_right, crop_bottom)
        cmd.extend(["-vf", crop_filter])
    else:
        cmd.extend(["-c:v", "copy"])

    cmd.extend([
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output)
    ])

    print(f"Merging video and audio...")
    print(f"  Video: {video}")
    print(f"  Audio: {audio}")
    print(f"  Skip: {audio_delay_ms}ms ({delay_seconds}s)")
    if has_crop:
        print(f"  Crop: left={crop_left}, top={crop_top}, right={crop_right}, bottom={crop_bottom}")
    print(f"  Output: {output}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")

    print(f"Successfully created: {output}")
    return output

def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge MP4 video with MP3 audio using FFmpeg"
    )
    parser.add_argument("--video", "-v", required=True, help="Path to the MP4 video file")
    parser.add_argument("--audio", "-a", required=True, help="Path to the MP3 audio file")
    parser.add_argument("--output", "-o", help="Path for the output file")
    parser.add_argument("--skip", "-s", type=int, default=0, help="Skip from start in ms (default: 10500)")
    parser.add_argument("--crop-left", type=int, default=190, help="Pixels to crop from left (default: 0)")
    parser.add_argument("--crop-top", type=int, default=38, help="Pixels to crop from top (default: 0)")
    parser.add_argument("--crop-right", type=int, default=190, help="Pixels to crop from right (default: 0)")
    parser.add_argument("--crop-bottom", type=int, default=45, help="Pixels to crop from bottom (default: 0)")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        merge_video_audio(
            args.video,
            args.audio,
            args.output,
            args.skip,
            args.crop_left,
            args.crop_top,
            args.crop_right,
            args.crop_bottom
        )
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

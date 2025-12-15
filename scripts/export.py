"""
Export script that combines video recording and audio merging.
Reads video version and audio path from the manifest, records the video,
and merges it with the audio.

Usage:
    python scripts/export.py
    python scripts/export.py --mode p  (portrait mode)
    python scripts/export.py --mode l  (landscape mode, default)
    python scripts/export.py --headless false  (show browser window)
"""

import argparse
import sys
import time
import requests
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

import os
# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.controllers.manifest_controller import ManifestController
from scripts.enums import AssetType


# ============================================================================
# FFmpeg Utilities
# ============================================================================

def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system PATH."""
    return shutil.which('ffmpeg') is not None


def convert_webm_to_mp4(webm_path: Path, mp4_path: Path, quality: str = 'high') -> bool:
    """Convert WebM to MP4 using ffmpeg with high quality settings."""
    if not check_ffmpeg_available():
        print("ffmpeg is not installed or not in PATH")
        return False

    print(f"\nConverting to MP4 with {quality} quality...")

    quality_settings = {
        'high': {'crf': '18', 'preset': 'slow', 'audio_bitrate': '320k'},
        'medium': {'crf': '23', 'preset': 'medium', 'audio_bitrate': '192k'},
        'low': {'crf': '28', 'preset': 'fast', 'audio_bitrate': '128k'}
    }

    settings = quality_settings.get(quality, quality_settings['high'])

    cmd = [
        'ffmpeg', '-i', str(webm_path),
        '-c:v', 'libx264', '-crf', settings['crf'], '-preset', settings['preset'],
        '-c:a', 'aac', '-b:a', settings['audio_bitrate'],
        '-movflags', '+faststart', '-pix_fmt', 'yuv420p', '-y',
        str(mp4_path)
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print(f"MP4 conversion complete: {mp4_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during MP4 conversion: {e.stderr}")
        return False


def ms_to_seconds(ms: int) -> float:
    """Convert milliseconds to seconds."""
    return ms / 1000.0


def build_crop_filter(left: int, top: int, right: int, bottom: int) -> str:
    """Build FFmpeg crop filter string."""
    return f"crop=iw-{left}-{right}:ih-{top}-{bottom}:{left}:{top}"


# ============================================================================
# Video Merge Functions
# ============================================================================

def merge_video_audio(
    video_path: str,
    audio_path: str,
    output_path: str = None,
    audio_delay_ms: int = 10000,
    crop_left: int = 190,
    crop_top: int = 38,
    crop_right: int = 190,
    crop_bottom: int = 45
) -> Path:
    """Merge an MP4 video file with an MP3 audio file."""
    video = Path(video_path)
    audio = Path(audio_path)

    if not video.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not audio.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if output_path:
        output = Path(output_path)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output = video.parent / f"{video.stem}_final_{timestamp}.mp4"

    output.parent.mkdir(parents=True, exist_ok=True)

    delay_seconds = ms_to_seconds(audio_delay_ms)
    has_crop = any([crop_left, crop_top, crop_right, crop_bottom])

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(delay_seconds),
        "-i", str(video),
        "-i", str(audio),
    ]

    if has_crop:
        crop_filter = build_crop_filter(crop_left, crop_top, crop_right, crop_bottom)
        cmd.extend(["-vf", crop_filter])
    else:
        cmd.extend(["-c:v", "copy"])

    cmd.extend(["-map", "0:v:0", "-map", "1:a:0", str(output)])

    print(f"\nMerging video and audio...")
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


# ============================================================================
# Video Recording Functions
# ============================================================================

def check_server_running(url: str, max_retries: int = 3, retry_delay: int = 2) -> bool:
    """Check if the server is running by making HTTP requests."""
    print(f"Checking if server is running at {url}...")

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"Server is running at {url}")
                return True
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"  Attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"Server is not running at {url}")
                return False
        except requests.exceptions.Timeout:
            print(f"  Request timed out (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    return False


def wait_for_video_player_ready(page: Page, timeout: int = 30000, wait_delay: int = 4) -> bool:
    """Wait for video player component to be ready."""
    try:
        print("Waiting for video player component (#video-player-recording)...")
        page.wait_for_selector('#video-player-recording', timeout=timeout, state='visible')
        print(f"Video player component is visible")
        print(f"  Waiting {wait_delay} seconds for video to initialize...")
        time.sleep(wait_delay)
        print("Video player is ready")
        return True
    except PlaywrightTimeoutError:
        print("Video player component (#video-player-recording) did not appear in time")
        return False


def click_fullscreen(page: Page) -> bool:
    """Click the fullscreen button."""
    try:
        print("Clicking fullscreen button...")
        fullscreen_selectors = [
            'media-fullscreen-button',
            'button[aria-label="Fullscreen"]',
            'button[aria-label="Enter fullscreen"]',
            'button[title="Fullscreen"]',
        ]

        for selector in fullscreen_selectors:
            try:
                button = page.query_selector(selector)
                if button:
                    button.click()
                    print(f"Fullscreen button clicked (selector: {selector})")
                    time.sleep(1)
                    return True
            except:
                continue

        page.keyboard.press('f')
        time.sleep(1)
        return True

    except Exception as e:
        print(f"  Warning: Could not enter fullscreen: {e}")
        return False


def turn_off_captions(page: Page) -> bool:
    """Turn off captions/subtitles if they are enabled."""
    try:
        print("Turning off captions...")
        caption_selectors = [
            'button[title="Hide captions"]',
            'button[title="Show captions"]',
            'button[aria-label="Subtitle Off"]',
            'button[aria-label="Subtitle On"]',
        ]

        for selector in caption_selectors:
            try:
                button = page.query_selector(selector)
                if button:
                    title = button.get_attribute('title') or ''
                    aria_label = button.get_attribute('aria-label') or ''

                    if 'hide captions' in title.lower():
                        button.click()
                        print("Clicked caption button to turn off captions")
                        time.sleep(0.5)
                        return True

                    if 'show captions' in title.lower():
                        print("Captions already off")
                        return True

                    if 'subtitle off' in aria_label.lower():
                        button.click()
                        print("Clicked caption button to turn off captions")
                        time.sleep(0.5)
                        return True

                    if 'subtitle on' in aria_label.lower():
                        print("Captions already off")
                        return True
            except:
                continue

        print("  No caption button found, assuming captions are off")
        return True

    except Exception as e:
        print(f"  Warning: Could not toggle captions: {e}")
        return True


def click_play(page: Page) -> bool:
    """Click the play button."""
    try:
        print("Clicking play button...")

        try:
            thumbnail_play_button = page.query_selector('div.absolute.inset-0.z-20 button.group.relative')
            if thumbnail_play_button:
                thumbnail_play_button.click()
                print("Thumbnail play button clicked")
                time.sleep(0.5)
                return True
        except:
            pass

        play_selectors = [
            'media-play-button',
            'button[aria-label="Play"]',
            'button[title="Play"]',
        ]

        for selector in play_selectors:
            try:
                button = page.query_selector(selector)
                if button:
                    button.click()
                    print(f"Play button clicked (selector: {selector})")
                    time.sleep(0.5)
                    return True
            except:
                continue

        page.keyboard.press('Space')
        time.sleep(0.5)
        return True

    except Exception as e:
        print(f"Could not click play button: {e}")
        return False


def get_video_duration(page: Page) -> float:
    """Get video duration from audio element."""
    try:
        duration_ms = page.evaluate("""
            () => {
                const audio = document.querySelector('audio');
                if (audio && audio.duration) {
                    return audio.duration * 1000;
                }
                return 0;
            }
        """)

        if duration_ms > 0:
            duration_sec = duration_ms / 1000
            print(f"Video duration: {duration_sec:.1f} seconds ({duration_sec/60:.1f} minutes)")
            return duration_sec

        return 0
    except Exception as e:
        print(f"  Warning: Could not get video duration: {e}")
        return 0


def record_video(version: str, mode: str = 'l', base_url: str = "http://localhost:5173",
                 headless: bool = True, output_dir: str = "./recordings") -> Path:
    """Record video from the React video player and return the recorded file path."""
    url = f"{base_url}/{version}/{mode}"
    mode_suffix = f"-{mode}" if mode else "l"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = f"Video-v{version}{mode_suffix}_{timestamp}.mp4"
    output_path = Path(output_dir) / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Recording Configuration:")
    print(f"  URL: {url}")
    print(f"  Mode: {'Portrait' if mode == 'p' else 'Landscape'} ({mode})")
    print(f"  Output: {output_path}")
    print(f"  Headless: {headless}")
    print(f"{'='*60}\n")

    if not check_server_running(base_url):
        print(f"\nError: Please start the development server first:")
        print(f"  cd visualise_video && npm run dev")
        raise RuntimeError("Server not running")

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=headless, args=['--mute-audio'])

        viewport_width = 1708   # 1708
        viewport_height = 827   # 827          
        record_width = 1700   # 1700
        record_height = 827   # 827

        context = browser.new_context(
            viewport={'width': viewport_width, 'height': viewport_height},
            record_video_dir=str(output_path.parent),
            record_video_size={'width': record_width, 'height': record_height},
            device_scale_factor=3,
            no_viewport=False,
            screen={'width': viewport_width, 'height': viewport_height},
        )

        page = context.new_page()

        try:
            print(f"Navigating to {url}...")
            page.goto(url, wait_until='networkidle')
            time.sleep(0.5)

            if not wait_for_video_player_ready(page, timeout=30000, wait_delay=4):
                raise RuntimeError("Video player component did not load properly")

            click_fullscreen(page)
            turn_off_captions(page)

            if not click_play(page):
                raise RuntimeError("Could not start video playback")

            print("Hiding UI elements...")
            page.keyboard.down("Control")
            page.keyboard.press("h")
            page.keyboard.up("Control")
            time.sleep(0.5)

            duration = get_video_duration(page)

            if duration > 0:
                wait_time = duration + 5
                print(f"Recording video... (waiting {wait_time:.1f} seconds)")
                start_time = time.time()
                while time.time() - start_time < wait_time:
                    elapsed = time.time() - start_time
                    progress = (elapsed / wait_time) * 100
                    print(f"  Progress: {progress:.1f}% ({elapsed:.1f}s / {wait_time:.1f}s)", end='\r')
                    time.sleep(1)
                print()
            else:
                print("Could not determine video duration, recording for 60 seconds...")
                time.sleep(60)

            print("Recording complete")

        finally:
            print("Finalizing video...")
            page.close()
            context.close()
            browser.close()

    # Rename the generated video file
    video_files = list(output_path.parent.glob("*.webm"))
    if not video_files:
        raise RuntimeError("No video file was created")

    latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
    webm_output = output_path.with_suffix('.webm')
    latest_video.rename(webm_output)
    print(f"\nWebM video saved to: {webm_output}")

    # Convert to MP4
    if check_ffmpeg_available():
        mp4_output = output_path.with_suffix('.mp4')
        if convert_webm_to_mp4(webm_output, mp4_output, quality='high'):
            print(f"MP4 saved to: {mp4_output}")
            return mp4_output

    return webm_output


# ============================================================================
# Main Export Function
# ============================================================================

def export_video(mode: str = 'l', headless: bool = False, base_url: str = "http://localhost:5173",
                 skip_ms: int = 10500, crop_left: int = 190, crop_top: int = 38,
                 crop_right: int = 190, crop_bottom: int = 45) -> Path:
    """
    Main export function that:
    1. Reads video version and audio path from manifest
    2. Records the video
    3. Merges video with audio
    """
    # Get manifest data
    manifest = ManifestController()

    video_data = manifest.get_field(AssetType.VIDEO)
    audio_data = manifest.get_field(AssetType.AUDIO)

    if not video_data or not video_data.get('version'):
        raise ValueError("Video version not found in manifest. Please generate video first.")

    if not audio_data or not audio_data.get('path'):
        raise ValueError("Audio path not found in manifest. Please generate audio first.")

    version = str(video_data['version'])
    audio_path = audio_data['path']

    print(f"\n{'='*60}")
    print(f"Export Configuration (from manifest):")
    print(f"  Video Version: {version}")
    print(f"  Audio Path: {audio_path}")
    print(f"  Mode: {'Portrait' if mode == 'p' else 'Landscape'}")
    print(f"  Headless: {headless}")
    print(f"  Base URL: {base_url}")
    print(f"  Skip (ms): {skip_ms}")
    print(f"  Crop: left={crop_left}, top={crop_top}, right={crop_right}, bottom={crop_bottom}")
    print(f"{'='*60}\n")

    # Step 1: Record the video
    print("\n[Step 1/2] Recording video...")
    recorded_video = record_video(
        version=version,
        mode=mode,
        base_url=base_url,
        headless=headless
    )

    # Step 2: Merge video with audio
    print("\n[Step 2/2] Merging video with audio...")
    final_output = merge_video_audio(
        video_path=str(recorded_video),
        audio_path=audio_path,
        audio_delay_ms=skip_ms,
        crop_left=crop_left,
        crop_top=crop_top,
        crop_right=crop_right,
        crop_bottom=crop_bottom
    )

    print(f"\n{'='*60}")
    print(f"Export complete!")
    print(f"  Final video: {final_output}")
    print(f"{'='*60}\n")

    return final_output


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export video by recording and merging with audio from manifest"
    )
    parser.add_argument('--mode', type=str, choices=['p', 'l'], default='l',
                        help='Video mode: p (portrait) or l (landscape). Default: l')
    parser.add_argument('--base-url', type=str, default='http://localhost:5173',
                        help='Base URL of the server (default: http://localhost:5173)')
    parser.add_argument('--headless', type=lambda x: str(x).lower() == 'true',
                        default=False, metavar='true|false',
                        help='Run browser in headless mode: true or false (default: true)')
    parser.add_argument('--skip', '-s', type=int, default=10500,
                        help='Skip from start in ms (default: 10500)')
    parser.add_argument('--crop-left', type=int, default=190,
                        help='Pixels to crop from left (default: 190)')
    parser.add_argument('--crop-top', type=int, default=38,
                        help='Pixels to crop from top (default: 38)')
    parser.add_argument('--crop-right', type=int, default=190,
                        help='Pixels to crop from right (default: 190)')
    parser.add_argument('--crop-bottom', type=int, default=45,
                        help='Pixels to crop from bottom (default: 45)')
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    try:
        export_video(
            mode=args.mode,
            headless=args.headless,
            base_url=args.base_url,
            skip_ms=args.skip,
            crop_left=args.crop_left,
            crop_top=args.crop_top,
            crop_right=args.crop_right,
            crop_bottom=args.crop_bottom
        )
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

import argparse
from math import ceil
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

import requests
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import os
# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.controllers.output_controller import OutputController
from scripts.controllers.manifest_controller import ManifestController
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.enums import AssetType
from scripts.merge_video_audio import merge_video_audio


DEFAULT_BASE_URL = "http://localhost:5173"
OUTPUT_DIR = "Outputs/Recordings"

VIEWPORT_WIDTH = 1700
VIEWPORT_HEIGHT = 827

QUALITY_PRESETS = {
    'high': {'crf': '18', 'preset': 'slow', 'audio_bitrate': '320k'},
    'medium': {'crf': '23', 'preset': 'medium', 'audio_bitrate': '192k'},
    'low': {'crf': '28', 'preset': 'fast', 'audio_bitrate': '128k'}
}

MANIFEST_CONTROLLER = ManifestController()
OUTPUT_CONTROLLER = OutputController()


def is_ffmpeg_available() -> bool:
    return shutil.which('ffmpeg') is not None


def print_ffmpeg_install_instructions():
    print("✗ ffmpeg is not installed or not in PATH")
    print("  Please install ffmpeg to enable MP4 conversion:")
    print("  - Windows: choco install ffmpeg  or  scoop install ffmpeg")
    print("  - Mac: brew install ffmpeg")
    print("  - Linux: sudo apt install ffmpeg")


def convert_webm_to_mp4(webm_path: Path, mp4_path: Path, quality: str = 'high') -> bool:
    if not is_ffmpeg_available():
        print_ffmpeg_install_instructions()
        return False

    print(f"\nConverting to MP4 with {quality} quality...")
    settings = QUALITY_PRESETS.get(quality, QUALITY_PRESETS['high'])

    cmd = [
        'ffmpeg',
        '-i', str(webm_path),
        '-c:v', 'libx264',
        '-crf', settings['crf'],
        '-preset', settings['preset'],
        '-c:a', 'aac',
        '-b:a', settings['audio_bitrate'],
        '-movflags', '+faststart',
        '-pix_fmt', 'yuv420p',
        '-y',
        str(mp4_path)
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print(f"✓ MP4 conversion complete: {mp4_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during MP4 conversion:\n  {e.stderr}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during conversion: {e}")
        return False


def is_server_running(url: str, max_retries: int = 1, retry_delay: int = 2) -> bool:
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ Server is running at {url}")
                return True
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"  Attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"✗ Server is not running at {url}")
                return False
        except requests.exceptions.Timeout:
            print(f"  Request timed out (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    return False


def ensure_server_running(base_url: str):
    if is_server_running(base_url):
        return None

    print("\nServer not running. Starting development server...")
    visualise_video_path = Path(project_root) / "visualise_video"
    server_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(visualise_video_path),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    max_wait = 30
    for i in range(max_wait):
        time.sleep(1)
        if is_server_running(base_url):
            print("Server started successfully!")
            return server_process
        if i == max_wait - 1:
            print("Error: Server failed to start within 30 seconds")
            server_process.terminate()
            return False
    time.sleep(1)
    return False


def wait_for_video_player(page: Page, timeout: int = 30000, init_delay: int = 4) -> bool:
    try:
        print("Waiting for video player component (#video-player-recording)...")
        page.wait_for_selector('#video-player-recording', timeout=timeout, state='visible')
        print("✓ Video player component is visible")

        print(f"  Waiting {init_delay} seconds for video to initialize...")
        time.sleep(init_delay)
        print("✓ Video player is ready")
        return True
    except PlaywrightTimeoutError:
        print("✗ Video player component (#video-player-recording) did not appear in time")
        print("  Make sure you're using the dynamic video page URL: /{lesson}/{material}/{version}")
        return False


def enter_fullscreen(page: Page) -> bool:
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
                    print(f"✓ Fullscreen button clicked (selector: {selector})")
                    time.sleep(1)
                    return True
            except Exception as e:
                print(f"  Selector '{selector}' failed: {e}")
                continue

        print("  Trying 'F' key for fullscreen...")
        page.keyboard.press('f')
        time.sleep(1)
        return True
    except Exception as e:
        print(f"  Warning: Could not enter fullscreen: {e}")
        return False


def disable_captions(page: Page) -> bool:
    try:
        print("Turning off captions...")
        caption_selectors = [
            'button[title="Hide captions"]',
            'button[title="Show captions"]',
            'button[aria-label="Subtitle Off"]',
            'button[aria-label="Subtitle On"]',
            'button[aria-label="Captions"]',
            'button[aria-label="Subtitles"]',
            'button[aria-label="Toggle captions"]',
            'button[aria-label="Toggle subtitles"]',
            'button[title="Captions"]',
            'button[title="Subtitles"]',
        ]

        for selector in caption_selectors:
            try:
                button = page.query_selector(selector)
                if not button:
                    continue

                title = button.get_attribute('title') or ''
                aria_label = button.get_attribute('aria-label') or ''

                if 'hide captions' in title.lower():
                    button.click()
                    print("✓ Clicked caption button to turn off captions")
                    time.sleep(0.5)
                    return True

                if 'show captions' in title.lower():
                    print("✓ Captions already off")
                    return True

                if 'subtitle off' in aria_label.lower() or 'captions off' in aria_label.lower():
                    button.click()
                    print("✓ Clicked caption button to turn off captions")
                    time.sleep(0.5)
                    return True

                if 'subtitle on' in aria_label.lower() or 'captions on' in aria_label.lower():
                    print("✓ Captions already off")
                    return True

                aria_pressed = button.get_attribute('aria-pressed')
                class_name = button.get_attribute('class') or ''

                if aria_pressed == 'true' or 'active' in class_name.lower():
                    button.click()
                    print("✓ Captions turned off")
                    time.sleep(0.5)
                    return True
            except:
                continue

        print("  No caption button found, assuming captions are off")
        return True
    except Exception as e:
        print(f"  Warning: Could not toggle captions: {e}")
        return True


def start_playback(page: Page) -> bool:
    try:
        print("Clicking play button...")

        try:
            thumbnail_play = page.query_selector('div.absolute.inset-0.z-20 button.group.relative')
            if thumbnail_play:
                thumbnail_play.click()
                print("✓ Thumbnail play button clicked")
                time.sleep(0.5)
                return True
        except Exception as e:
            print(f"  No thumbnail play button found: {e}")

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
                    print(f"✓ Play button clicked (selector: {selector})")
                    time.sleep(0.5)
                    return True
            except Exception as e:
                print(f"  Selector '{selector}' failed: {e}")
                continue

        print("  Trying space bar to play...")
        page.keyboard.press('Space')
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"✗ Could not click play button: {e}")
        return False


def hide_ui_elements(page: Page):
    print("Hiding UI elements...")
    page.keyboard.down("Control")
    page.keyboard.press("h")
    page.keyboard.up("Control")
    time.sleep(0.5)


def get_video_duration(page: Page) -> float:
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
            print(f"✓ Video duration: {duration_sec:.1f} seconds ({duration_sec/60:.1f} minutes)")
            return duration_sec

        return 0
    except Exception as e:
        print(f"  Warning: Could not get video duration: {e}")
        return 0


def wait_for_recording_completion(duration: float):
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


def save_webm_recording(webm_output_path: Path) -> bool:
    try:
        video_files = list(webm_output_path.parent.glob("*.webm"))
        if not video_files:
            print("✗ Error: No video file was created")
            return False

        video_files[0].rename(webm_output_path)
        print(f"\n✓ WebM video saved to: {webm_output_path}")
        return True
    except Exception as e:
        print(f"✗ Error saving video: {e}")
        return False

def save_mp4_recording(mp4_output_path: Path, webm_output_path: Path) -> bool:
    if is_ffmpeg_available():
        if convert_webm_to_mp4(webm_output_path, mp4_output_path, quality='high'):
            print(f"✓ MP4 video saved to: {mp4_output_path}")
            return True
        else:
            print(f"✗ Failed to convert to MP4")
            return False
    else:
        print("\n✗ Error: MP4 Install ffmpeg to enable MP4 conversion")
        print_ffmpeg_install_instructions()
        return False

def record_video(version: int, mode: str = 'l', base_url: str = DEFAULT_BASE_URL,
                 headless: bool = False) -> Tuple[bool, Path]:
    url = f"{base_url}/{version}/{mode}"
    recording_version = OUTPUT_CONTROLLER.getLatestVersionByDirectory(OUTPUT_DIR) + 1
    mp4_output_filename = f"v{recording_version}/recording_v{recording_version}.mp4"
    webm_output_filename = f"v{recording_version}/recording_v{recording_version}.webm"
    mp4_output_path = Path(OUTPUT_DIR) / mp4_output_filename
    webm_output_path = Path(OUTPUT_DIR) / webm_output_filename
    mp4_output_path.parent.mkdir(parents=True, exist_ok=True)
    webm_output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("Recording Configuration:")
    print(f"  URL: {url}")
    print(f"  Mode: {'Portrait' if mode == 'p' else 'Landscape'} ({mode})")
    print(f"  Output: {mp4_output_path}")
    print(f"  Output: {webm_output_path}")
    print(f"  Headless: {headless}")
    print(f"{'='*60}\n")

    server_process = ensure_server_running(base_url)
    if server_process is False:
        return False, None

    recording_successful = False

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=headless, args=['--mute-audio'])

        context = browser.new_context(
            viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT},
            record_video_dir=str(webm_output_path.parent),
            record_video_size={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT},
            device_scale_factor=3,
            screen={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT},
        )

        page = context.new_page()

        try:
            print(f"Navigating to {url}...")
            page.goto(url, wait_until='networkidle')
            time.sleep(0.5)

            if not wait_for_video_player(page, timeout=30000, init_delay=4):
                print("Error: Video player component did not load properly")
                return False, None

            enter_fullscreen(page)
            disable_captions(page)

            if not start_playback(page):
                print("Error: Could not start video playback")
                return False, None

            hide_ui_elements(page)

            duration = get_video_duration(page)
            wait_for_recording_completion(duration)

            print("✓ Recording complete")
            recording_successful = True

        except Exception as e:
            print(f"✗ Error during recording: {e}")
            return False, None

        finally:
            print("Finalizing video...")
            page.close()
            context.close()
            browser.close()

    # Save video files AFTER browser context is fully closed
    success = False
    output_path = None

    if recording_successful:
        if save_webm_recording(webm_output_path):
            if save_mp4_recording(mp4_output_path, webm_output_path):
                success = True
                output_path = mp4_output_path
            else:
                print(f"\n✗ Recording failed: MP4 conversion required but unsuccessful")

    if server_process:
        print("Stopping development server...")
        server_process.terminate()

    return success, output_path


def get_video_version() -> int:
    video_info = MANIFEST_CONTROLLER.get_field(AssetType.VIDEO)

    if not video_info or video_info.get('version') is None:
        print("✗ Error: No video version found in manifest")
        sys.exit(1)

    return video_info['version']


def main():
    parser = argparse.ArgumentParser(description='Record video lessons from the React video player')

    parser.add_argument('--base-url', type=str, default=DEFAULT_BASE_URL,
                        help=f'Base URL of the server (default: {DEFAULT_BASE_URL})')
    parser.add_argument('--headless', type=lambda x: str(x).lower() == 'true',
                        default=False, metavar='true|false',
                        help='Run browser in headless mode: true or false (default: false)')

    args = parser.parse_args()

    version = get_video_version()
    print(f"✓ Using video version {version} from manifest")

    success, mp4_path = record_video(
        version=version,
        mode='l',
        base_url=args.base_url,
        headless=args.headless,
    )
    time.sleep(2)
    if success:
        # Merge video with audio from manifest
        audio_info = MANIFEST_CONTROLLER.get_field(AssetType.AUDIO)
        if audio_info and audio_info.get('path'):
            # Normalize path for cross-platform compatibility
            io_controller = SystemIOController()
            audio_path = io_controller.normalize_path(audio_info['path'])
            merged_output_path = mp4_path.parent / f"{mp4_path.stem}_merged.mp4"
            print(f"\nMerging video with audio...")
            merge_video_audio(
                video_path=str(mp4_path),
                audio_path=audio_path,
                output_path=str(merged_output_path),
                audio_delay_ms=9500,
            )
        else:
            print("⚠ No audio found in manifest, skipping merge")

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

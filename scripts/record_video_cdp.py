import argparse
import base64
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import requests
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

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

MANIFEST_CONTROLLER = ManifestController()
OUTPUT_CONTROLLER = OutputController()


class CDPScreenRecorder:
    def __init__(self, page: Page, output_dir: Path, width: int = 1700, height: int = 827,
                 quality: int = 100, fps: int = 30, format: str = "jpeg"):
        self.page = page
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.quality = quality
        self.fps = fps
        self.format = format
        self.recording = False
        self.frame_count = 0
        self.dropped_frames = 0
        self.capture_errors = []
        self.cdp_session = None
        self.frames_dir = None

    def _get_file_extension(self) -> str:
        return "png" if self.format == "png" else "jpg"

    def start(self):
        self.frames_dir = self.output_dir / "frames_temp"

        if self.frames_dir.exists():
            print("  Cleaning up existing frames from previous recording...")
            self._cleanup_frames()

        self.frames_dir.mkdir(parents=True, exist_ok=True)

        try:
            print("  Creating CDP session...")
            self.cdp_session = self.page.context.new_cdp_session(self.page)
            self.recording = True
            print(f"[OK] CDP session ready for screenshot capture")
            print(f"  Format: {self.format.upper()}, Quality: {self.quality}")
            print(f"  Resolution: {self.width}x{self.height}")
        except Exception as e:
            print(f"✗ Failed to create CDP session: {e}")
            import traceback
            traceback.print_exc()
            raise

    def capture_frame(self):
        if not self.recording or not self.cdp_session:
            return False

        try:
            result = self.cdp_session.send("Page.captureScreenshot", {
                "format": self.format,
                "quality": self.quality if self.format == "jpeg" else None,
                "clip": {
                    "x": 0,
                    "y": 0,
                    "width": self.width,
                    "height": self.height,
                    "scale": 1
                }
            })

            frame_data = base64.b64decode(result["data"])
            frame_path = self.frames_dir / f"frame_{self.frame_count:06d}.{self._get_file_extension()}"

            with open(frame_path, "wb") as f:
                f.write(frame_data)

            self.frame_count += 1
            return True
        except Exception as e:
            self.dropped_frames += 1
            error_msg = f"Frame {self.frame_count + self.dropped_frames}: {type(e).__name__}: {str(e)}"

            if len(self.capture_errors) < 10:
                self.capture_errors.append(error_msg)

            if self.dropped_frames % 30 == 0:
                print(f"\n  Warning: {self.dropped_frames} frames dropped so far")

            return False

    def record_duration(self, duration: float, show_progress: bool = True):
        start_time = time.time()
        last_progress_update = start_time

        while time.time() - start_time < duration:
            current_time = time.time()
            elapsed = current_time - start_time
            expected_frame = int(elapsed * self.fps)

            if expected_frame > self.frame_count:
                self.capture_frame()

            if show_progress and (current_time - last_progress_update) >= 0.5:
                progress = (elapsed / duration) * 100
                capture_rate = (self.frame_count / (self.frame_count + self.dropped_frames) * 100) if (self.frame_count + self.dropped_frames) > 0 else 100
                print(f"  Progress: {progress:.1f}% | Frames: {self.frame_count} | Dropped: {self.dropped_frames} | Success: {capture_rate:.1f}% | Time: {elapsed:.1f}s / {duration:.1f}s", end='\r')
                last_progress_update = current_time
            else:
                next_frame_time = start_time + (self.frame_count / self.fps)
                sleep_time = next_frame_time - current_time
                if sleep_time > 0.001:
                    time.sleep(min(sleep_time * 0.9, 0.01))
                elif sleep_time > 0:
                    time.sleep(0.001)

        if show_progress:
            print()

    def stop(self, output_filename: str = "output_hq.mp4") -> Optional[Path]:
        self.recording = False

        try:
            if self.cdp_session:
                self.cdp_session.detach()
        except Exception as e:
            print(f"  Warning: Error detaching CDP session: {e}")

        total_attempts = self.frame_count + self.dropped_frames
        success_rate = (self.frame_count / total_attempts * 100) if total_attempts > 0 else 0
        print(f"\n{'='*60}")
        print(f"Recording Statistics:")
        print(f"  Captured frames: {self.frame_count}")
        print(f"  Dropped frames: {self.dropped_frames}")
        print(f"  Success rate: {success_rate:.1f}%")
        if self.capture_errors:
            print(f"  Sample errors (first {len(self.capture_errors)}):")
            for error in self.capture_errors[:3]:
                print(f"    - {error}")
        print(f"{'='*60}\n")

        if self.frame_count == 0:
            print("✗ No frames captured!")
            return None

        output_video = self.output_dir / output_filename
        ext = self._get_file_extension()

        print(f"Compiling video with ffmpeg...")
        print(f"  Input: {self.frame_count} {ext.upper()} frames")
        print(f"  Output: {output_video}")
        print(f"  FPS: {self.fps}")

        cmd = [
            'ffmpeg',
            '-y',
            '-framerate', str(self.fps),
            '-i', str(self.frames_dir / f'frame_%06d.{ext}'),
            '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
            '-c:v', 'libx264',
            '-crf', '15',
            '-preset', 'slow',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            str(output_video)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"[OK] Video compiled successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ FFmpeg error: {e.stderr}")
            return None

        if output_video.exists():
            size_mb = output_video.stat().st_size / (1024 * 1024)
            print(f"[OK] Output file size: {size_mb:.2f} MB")

        return output_video

    def _cleanup_frames(self):
        if not self.frames_dir or not self.frames_dir.exists():
            return

        try:
            shutil.rmtree(self.frames_dir)
            print(f"[OK] Cleaned up temporary frames")
        except PermissionError as e:
            print(f"  Warning: Permission denied cleaning frames: {e}")
            print(f"  Please manually delete: {self.frames_dir}")
        except Exception as e:
            print(f"  Warning: Could not cleanup frames: {e}")
            print(f"  Please manually delete: {self.frames_dir}")


def is_ffmpeg_available() -> bool:
    return shutil.which('ffmpeg') is not None


def print_ffmpeg_install_instructions():
    print("✗ ffmpeg is not installed or not in PATH")
    print("  Please install ffmpeg to enable MP4 conversion:")
    print("  - Windows: choco install ffmpeg  or  scoop install ffmpeg")
    print("  - Mac: brew install ffmpeg")
    print("  - Linux: sudo apt install ffmpeg")


def is_server_running(url: str, max_retries: int = 1, retry_delay: int = 2) -> bool:
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"[OK] Server is running at {url}")
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


def ensure_server_running(base_url: str) -> Optional[subprocess.Popen]:
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
        print("[OK] Video player component is visible")

        print(f"  Waiting {init_delay} seconds for video to initialize...")
        time.sleep(init_delay)
        print("[OK] Video player is ready")
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
                    print(f"[OK] Fullscreen button clicked (selector: {selector})")
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
                    print("[OK] Clicked caption button to turn off captions")
                    time.sleep(0.5)
                    return True

                if 'show captions' in title.lower():
                    print("[OK] Captions already off")
                    return True

                if 'subtitle off' in aria_label.lower() or 'captions off' in aria_label.lower():
                    button.click()
                    print("[OK] Clicked caption button to turn off captions")
                    time.sleep(0.5)
                    return True

                if 'subtitle on' in aria_label.lower() or 'captions on' in aria_label.lower():
                    print("[OK] Captions already off")
                    return True

                aria_pressed = button.get_attribute('aria-pressed')
                class_name = button.get_attribute('class') or ''

                if aria_pressed == 'true' or 'active' in class_name.lower():
                    button.click()
                    print("[OK] Captions turned off")
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
                print("[OK] Thumbnail play button clicked")
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
                    print(f"[OK] Play button clicked (selector: {selector})")
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
    page.keyboard.down("Control")
    page.keyboard.press("h")
    page.keyboard.up("Control")


def calculate_buffer_time(duration: float) -> int:
    if duration < 30:
        return 4
    elif duration < 300:
        return 6
    else:
        return 8


def wait_for_recording_completion(duration: float, recorder):
    if duration > 0:
        buffer = calculate_buffer_time(duration)
        wait_time = duration + buffer
        print(f"\nRecording video...")
        print(f"  Duration: {duration:.1f}s + {buffer}s buffer = {wait_time:.1f}s total")
        recorder.record_duration(wait_time)
    else:
        print("Could not determine video duration, recording for 60 seconds...")
        recorder.record_duration(60)


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
            print(f"[OK] Video duration: {duration_sec:.1f} seconds ({duration_sec/60:.1f} minutes)")
            return duration_sec

        return 0
    except Exception as e:
        print(f"  Warning: Could not get video duration: {e}")
        return 0


def record_video_cdp(version: int, mode: str = 'l', base_url: str = DEFAULT_BASE_URL,
                     headless: bool = False, quality: int = 100, fps: int = 30,
                     format: str = "jpeg", debug: bool = False) -> Tuple[bool, Path]:

    if not is_ffmpeg_available():
        print("✗ ffmpeg is required for CDP recording")
        print_ffmpeg_install_instructions()
        return False, None

    url = f"{base_url}/{version}/{mode}"
    recording_version = OUTPUT_CONTROLLER.getLatestVersionByDirectory(OUTPUT_DIR) + 1
    mp4_output_filename = f"v{recording_version}/recording_v{recording_version}_cdp.mp4"
    mp4_output_path = Path(OUTPUT_DIR) / mp4_output_filename
    mp4_output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("Recording Configuration:")
    print(f"  URL: {url}")
    print(f"  Mode: {'Portrait' if mode == 'p' else 'Landscape'} ({mode})")
    print(f"  Quality: {quality}%")
    print(f"  FPS: {fps}")
    print(f"  Format: {format.upper()}")
    print(f"  Resolution: {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}")
    print(f"  Output: {mp4_output_path}")
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
            device_scale_factor=3,
            screen={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT},
        )

        page = context.new_page()

        recorder = CDPScreenRecorder(
            page=page,
            output_dir=mp4_output_path.parent,
            width=VIEWPORT_WIDTH,
            height=VIEWPORT_HEIGHT,
            quality=quality,
            fps=fps,
            format=format
        )

        try:
            print(f"Navigating to {url}...")
            page.goto(url, wait_until='networkidle')
            time.sleep(0.5)

            if not wait_for_video_player(page, timeout=30000, init_delay=4):
                print("Error: Video player component did not load properly")
                return False, None

            enter_fullscreen(page)
            disable_captions(page)


            recorder.start()
            hide_ui_elements(page)

            if debug:
                debug_path = mp4_output_path.parent / f"debug_cdp_v{version}.png"
                page.screenshot(path=str(debug_path))
                print(f"  Debug screenshot: {debug_path}")


            duration = get_video_duration(page)
            wait_for_recording_completion(duration, recorder)

            print("[OK] Recording complete")
            recording_successful = True

        except Exception as e:
            print(f"✗ Error during recording: {e}")
            return False, None

        finally:
            print("\nFinalizing video...")
            output_path = recorder.stop(mp4_output_filename.split('/')[-1])

            page.close()
            context.close()
            browser.close()

    if server_process:
        print("Stopping development server...")
        server_process.terminate()

    if recording_successful and output_path and output_path.exists():
        print(f"\n[OK] Recording complete!")
        print(f"  Output: {output_path}")
        return True, output_path

    return False, None


def get_video_version() -> int:
    video_info = MANIFEST_CONTROLLER.get_field(AssetType.VIDEO)

    if not video_info or video_info.get('version') is None:
        print("✗ Error: No video version found in manifest")
        sys.exit(1)

    return video_info['version']


def main():
    parser = argparse.ArgumentParser(description='Record video lessons using CDP for high quality')

    parser.add_argument('--base-url', type=str, default=DEFAULT_BASE_URL,
                        help=f'Base URL of the server (default: {DEFAULT_BASE_URL})')
    parser.add_argument('--headless', type=lambda x: str(x).lower() == 'true',
                        default=False, metavar='true|false',
                        help='Run browser in headless mode: true or false (default: false)')
    parser.add_argument('--quality', type=int, default=100, choices=range(0, 101),
                        metavar='0-100',
                        help='Frame quality 0-100 (default: 100)')
    parser.add_argument('--fps', type=int, default=30,
                        help='Output video FPS (default: 30)')
    parser.add_argument('--format', type=str, choices=['jpeg', 'png'], default='jpeg',
                        help='Frame format: jpeg or png (default: jpeg)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')

    args = parser.parse_args()

    version = get_video_version()
    print(f"[OK] Using video version {version} from manifest")

    success, mp4_path = record_video_cdp(
        version=version,
        mode='l',
        base_url=args.base_url,
        headless=args.headless,
        quality=args.quality,
        fps=args.fps,
        format=args.format,
        debug=args.debug
    )
    time.sleep(2)
    print(f"mp4_path: {mp4_path}")
    if success:
        audio_info = MANIFEST_CONTROLLER.get_field(AssetType.AUDIO)
        if audio_info and audio_info.get('path'):
            io_controller = SystemIOController()
            audio_path = io_controller.normalize_path(audio_info['path'])
            merged_output_path = mp4_path.parent / f"{mp4_path.stem}_merged.mp4"
            print(f"\nMerging video with audio...")
            merge_video_audio(
                video_path=str(mp4_path),
                audio_path=audio_path,
                output_path=str(merged_output_path),
                audio_delay_ms=0,
            )
        else:
            print("⚠ No audio found in manifest, skipping merge")

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

import os
import sys
import argparse
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.video_build_service.s3_manager import S3Manager, S3Config, UploadFileParams
from scripts.video_build_service.react_build_manager import ReactBuildManager
from scripts.controllers.manifest_controller import ManifestController
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.enums import AssetType
from scripts.utility.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, PAYLOAD_API_BASE_URL, PAYLOAD_AUTH_TOKEN, WEBSITE_URL

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class BuildAndUploadService:
    def __init__(
        self,
        topic: str = "test-topic"
    ):
        self.topic = topic
        self.aws_access_key = AWS_ACCESS_KEY_ID
        self.aws_secret_key = AWS_SECRET_ACCESS_KEY
        self.aws_region = AWS_REGION
        self.bucket_name = 'outscal'
        self.project_root = self._get_project_root()
        self.logger = logging.getLogger('build_and_upload')

        # Set topic in controllers
        ManifestController().set_topic(topic)
        ClaudeCliConfig.set_topic(topic)

    @staticmethod
    def _get_project_root() -> Path:
        return Path(__file__).parent.parent.parent

    def get_paths_from_manifest(self) -> Dict[str, Any]:
        manifest = ManifestController()

        paths = {
            'video_path': None,
            'audio_path': None,
            'transcript_path': None,
            'video_version': None
        }

        # Get Video path and version
        video_data = manifest.get_field(AssetType.VIDEO)
        if video_data and video_data.get('path'):
            video_file_path = self.project_root / video_data['path']
            paths['video_path'] = str(video_file_path.parent)
            paths['video_version'] = video_data.get('version')

        # Get Audio path
        audio_data = manifest.get_field(AssetType.AUDIO)
        if audio_data and audio_data.get('path'):
            paths['audio_path'] = str(self.project_root / audio_data['path'])

        # Get Transcript path
        transcript_data = manifest.get_field(AssetType.TRANSCRIPT)
        if transcript_data and transcript_data.get('path'):
            paths['transcript_path'] = str(self.project_root / transcript_data['path'])

        return paths

    @staticmethod
    def find_main_video_file(video_path: Path) -> Optional[Path]:
        # First try Video-*.tsx pattern
        video_files = list(video_path.glob("Video-*.tsx"))
        if video_files:
            return video_files[0]

        # Try *Video*.tsx pattern (case insensitive check)
        for f in video_path.glob("*.tsx"):
            if "video" in f.stem.lower() and not f.stem.startswith("scene"):
                return f

        # If no video file found, look for any non-scene tsx file
        tsx_files = [f for f in video_path.glob("*.tsx") if not f.stem.startswith("scene")]
        if tsx_files:
            return tsx_files[0]

        return None

    @staticmethod
    def find_scene_files(video_path: Path) -> List[Path]:
        return list(video_path.glob("scene_*.tsx"))

    def build_video(self, tsx_path: str) -> Dict[str, Any]:
        build_manager = ReactBuildManager(self.project_root)
        return build_manager.build_component(tsx_path)

    @staticmethod
    def create_slug(title: str, version: int) -> str:
        slug = title.lower().replace(' ', '-').replace('_', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        return slug + f"_v{version}"

    def _initialize_s3(self) -> Optional[str]:
        if self.aws_access_key and self.aws_secret_key:
            S3Manager.get_instance(S3Config(
                access_key_id=self.aws_access_key,
                secret_access_key=self.aws_secret_key,
                region=self.aws_region
            ))
        else:
            return "AWS credentials not provided. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables or pass them as arguments."
        return None

    def create_video_entry(
        self,
        slug: str,
        audio_url: str,
        transcript_url: str,
        visualizer_url: str,
    ) -> Dict[str, Any]:
        if not PAYLOAD_API_BASE_URL or not PAYLOAD_AUTH_TOKEN:
            return {
                'success': False,
                'error': 'PAYLOAD_API_BASE_URL or PAYLOAD_AUTH_TOKEN not configured'
            }

        api_endpoint = f"{PAYLOAD_API_BASE_URL.rstrip('/')}/api/videos"

        payload = {
            'slug': slug,
            'audioUrl': audio_url,
            'transcriptUrl': transcript_url,
            'visulizerUrl': visualizer_url,
            'title': self.topic
        }

        response = requests.post(
            api_endpoint,
            json=payload,
            headers={
                'Authorization': f'users API-Key {PAYLOAD_AUTH_TOKEN}',
                'Content-Type': 'application/json'
            }
        )

        data = response.json()

        if response.status_code >= 400 or data.get('errors'):
            error_msg = data.get('errors', [{}])[0].get('message', 'Unknown error') if data.get('errors') else data.get('message', 'Request failed')
            self.logger.error(f"Failed to create video entry: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }

        self.logger.info(f"Created video entry with slug: {slug}")
        url=f"{WEBSITE_URL}/v2/video/{data.get('doc', {}).get('slug')}/{data.get('doc', {}).get('urltime')}"
        return url

    def upload_to_s3(
        self,
        js_file_path: str,
        audio_file_path: Optional[str],
        transcript_file_path: Optional[str],
        title: str,
        video_version: int
    ) -> Dict[str, Any]:
        errors = []
        urls = {}

        s3_manager = S3Manager.get_instance()
        if not s3_manager.is_initialized():
            errors.append("S3Manager not initialized. Please initialize with credentials first.")
            return {'success': False, 'urls': {}, 'errors': errors}

        slug = self.create_slug(title, video_version)
        version_folder = f"v{video_version}"

        # Upload video JS file
        if os.path.exists(js_file_path):
            try:
                with open(js_file_path, 'rb') as f:
                    js_content = f.read()

                s3_key = f"ReactVideo/{slug}/{version_folder}/video.js"
                video_url = s3_manager.upload_file_sync(UploadFileParams(
                    bucket_name=self.bucket_name,
                    file_path=s3_key,
                    file_data=js_content,
                    mime_type='application/javascript'
                ))
                urls['video_url'] = video_url
                self.logger.info(f"Uploaded video: {video_url}")
            except Exception as e:
                errors.append(f"Failed to upload video JS: {str(e)}")
        else:
            errors.append(f"JS file not found: {js_file_path}")

        # Upload audio file
        if audio_file_path and os.path.exists(audio_file_path):
            try:
                with open(audio_file_path, 'rb') as f:
                    audio_content = f.read()

                s3_key = f"ReactVideo/{slug}/{version_folder}/audio.mp3"
                audio_url = s3_manager.upload_file_sync(UploadFileParams(
                    bucket_name=self.bucket_name,
                    file_path=s3_key,
                    file_data=audio_content
                ))
                urls['audio_url'] = audio_url
                self.logger.info(f"Uploaded audio: {audio_url}")
            except Exception as e:
                errors.append(f"Failed to upload audio: {str(e)}")
        elif audio_file_path:
            errors.append(f"Audio file not found: {audio_file_path}")

        # Upload transcript file
        if transcript_file_path and os.path.exists(transcript_file_path):
            try:
                with open(transcript_file_path, 'rb') as f:
                    transcript_content = f.read()

                s3_key = f"ReactVideo/{slug}/{version_folder}/transcript.json"
                transcript_url = s3_manager.upload_file_sync(UploadFileParams(
                    bucket_name=self.bucket_name,
                    file_path=s3_key,
                    file_data=transcript_content,
                    mime_type='application/json'
                ))
                urls['transcript_url'] = transcript_url
                self.logger.info(f"Uploaded transcript: {transcript_url}")
            except Exception as e:
                errors.append(f"Failed to upload transcript: {str(e)}")
        elif transcript_file_path:
            errors.append(f"Transcript file not found: {transcript_file_path}")

        success = 'video_url' in urls and not errors
        return {'success': success, 'urls': urls, 'errors': errors}

    def run(self) -> Dict[str, Any]:
        title = self.topic
        manifest_paths = self.get_paths_from_manifest()
        video_path = manifest_paths['video_path']
        audio_path = manifest_paths['audio_path']
        transcript_path = manifest_paths['transcript_path']
        video_version = manifest_paths['video_version']

        if not video_path:
            return {
                'success': False,
                'error': "Video path not found in manifest"
            }

        if not video_version:
            return {
                'success': False,
                'error': "Video version not found in manifest"
            }

        video_dir = Path(video_path)

        if not video_dir.exists():
            return {
                'success': False,   
                'error': f"Video path does not exist: {video_path}"
            }

        # Find main video file
        main_tsx = self.find_main_video_file(video_dir)
        if not main_tsx:
            return {
                'success': False,
                'error': f"No main video TSX file found in: {video_path}"
            }

        self.logger.info(f"Found main video file: {main_tsx}")
        self.logger.info(f"Audio path: {audio_path}")
        self.logger.info(f"Transcript path: {transcript_path}")

        # Initialize S3Manager with credentials
        init_error = self._initialize_s3()
        if init_error:
            return {
                'success': False,
                'urls': {},
                'errors': [init_error]
            }

        # Step 1: Build the video
        self.logger.info("Building video component...")
        build_result = self.build_video(str(main_tsx))

        if not build_result['success']:
            return {
                'success': False,
                'urls': {},
                'errors': build_result.get('errors', ['Failed to build video'])
            }

        built_js_path = build_result['built_path']
        self.logger.info(f"Video built successfully: {built_js_path}")

        # Step 2: Upload to S3
        self.logger.info("Uploading to S3...")
        upload_result = self.upload_to_s3(
            js_file_path=built_js_path,
            audio_file_path=audio_path,
            transcript_file_path=transcript_path,
            title=title,
            video_version=video_version
        )
        url = self.create_video_entry(slug=self.create_slug(title,video_version),
         audio_url=upload_result['urls']['audio_url'],
         transcript_url=upload_result['urls']['transcript_url'],
         visualizer_url=upload_result['urls']['video_url'])
        ManifestController().update_deployed_videos(url)
        return {
            'success': True,
            'url': url,
            'upload_result': upload_result
        }


def main():
    parser = argparse.ArgumentParser(
        description='Build and upload video TSX to S3. All paths are read from manifest.json.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    # Use paths from manifest.json
    python build_and_upload.py

    # With custom topic
    python build_and_upload.py --topic "my-video"
        '''
    )

    parser.add_argument('--topic', help='Topic for the video (default: folder name)')

    args = parser.parse_args()

    service = BuildAndUploadService(topic=args.topic)

    result = service.run()

    if result['success']:
        sys.exit(0)
    else:
        sys.exit(1)



if __name__ == '__main__':
    main()

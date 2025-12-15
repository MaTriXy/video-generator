"""
S3Manager service for handling AWS S3 operations.
Standalone version for video build service.
"""

import boto3
from botocore.exceptions import ClientError
import os
from typing import Optional, Union
from dataclasses import dataclass
import mimetypes


@dataclass
class S3Config:
    """S3 configuration."""
    access_key_id: str
    secret_access_key: str
    region: str = 'ap-south-1'


@dataclass
class UploadFileParams:
    """Parameters for file upload."""
    bucket_name: str
    file_path: str
    file_data: Union[bytes, str]
    mime_type: Optional[str] = None
    acl: str = 'public-read'


class S3Manager:
    """Singleton S3Manager for AWS S3 operations."""

    _instance: Optional['S3Manager'] = None
    _s3_client = None
    _config: Optional[S3Config] = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls, config: Optional[S3Config] = None) -> 'S3Manager':
        """Get or create S3Manager instance with configuration."""
        instance = cls()

        if config:
            instance._config = config
            instance._s3_client = boto3.client(
                's3',
                region_name=config.region,
                aws_access_key_id=config.access_key_id,
                aws_secret_access_key=config.secret_access_key
            )

        return instance

    def _ensure_initialized(self) -> None:
        """Ensure S3 client is initialized."""
        if not self._s3_client or not self._config:
            raise RuntimeError(
                "S3Manager not initialized. Call get_instance with config first."
            )

    def _get_content_type(self, file_path: str, mime_type: Optional[str] = None) -> str:
        """Determine content type based on file extension."""
        if mime_type:
            return mime_type

        if '.cjs' in file_path or '.mjs' in file_path:
            return 'application/javascript'

        if '.data' in file_path or '.wasm' in file_path:
            return 'binary/octet-stream'

        if '.wasm.gz' in file_path or '.data.gz' in file_path:
            return 'application/x-gzip'

        extension_map = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.jsx': 'application/javascript',
            '.ts': 'application/typescript',
            '.tsx': 'application/typescript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
        }

        ext = os.path.splitext(file_path)[1].lower()

        if ext in extension_map:
            return extension_map[ext]

        guessed_type, _ = mimetypes.guess_type(file_path)
        return guessed_type or 'application/octet-stream'

    def _get_content_encoding(self, file_path: str) -> Optional[str]:
        """Get content encoding based on file extension."""
        if '.gz' in file_path:
            return 'gzip'
        if '.br' in file_path:
            return 'br'
        return None

    def upload_file_sync(self, params: UploadFileParams) -> str:
        """
        Synchronous file upload to S3.

        Returns:
            Public URL of uploaded file
        """
        self._ensure_initialized()

        upload_params = {
            'Bucket': params.bucket_name,
            'Key': params.file_path,
            'Body': params.file_data,
            'ACL': params.acl,
            'ContentType': self._get_content_type(params.file_path, params.mime_type)
        }

        content_encoding = self._get_content_encoding(params.file_path)
        if content_encoding:
            upload_params['ContentEncoding'] = content_encoding

        self._s3_client.put_object(**upload_params)

        region = self._config.region
        url = f"https://{params.bucket_name}.s3.{region}.amazonaws.com/{params.file_path}"

        return url

    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._s3_client is not None and self._config is not None

    def upload_from_file_path(self, local_file_path: str, bucket_name: str,
                             s3_key: str, acl: str = 'public-read') -> str:
        """
        Upload a file from local file system.

        Returns:
            Public URL of uploaded file
        """
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"File not found: {local_file_path}")

        with open(local_file_path, 'rb') as f:
            file_data = f.read()

        params = UploadFileParams(
            bucket_name=bucket_name,
            file_path=s3_key,
            file_data=file_data,
            acl=acl
        )

        return self.upload_file_sync(params)

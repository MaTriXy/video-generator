"""
Prompt Cache Controller for Langfuse Integration

This controller manages fetching prompts from Langfuse with local caching capabilities.
It can fetch prompts either from the cloud (Langfuse) or from local cache based on configuration.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langfuse import Langfuse
from scripts.utility.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
from scripts.logging_config import get_utility_logger

# Initialize logger
logger = get_utility_logger('controllers.prompt_cache')


class PromptCacheController:

    def __init__(self, use_cache: bool = False, cache_ttl_hours: int = 24*365):
        self.use_cache = use_cache
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_dir = Path("C:/Outscal/course-workflow/cache/prompts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.langfuse_client = None
        if not use_cache:
            try:
                self.langfuse_client = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_HOST
                )
                logger.info("PromptCacheController initialized with cloud fetching enabled")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse client: {e}")
                logger.info("Falling back to cache mode")
                self.use_cache = True
        else:
            logger.info("PromptCacheController initialized with cache mode enabled")

    def fetch_prompt(self, prompt_name: str, tag: Optional[str] = "production") -> Optional[Dict[str, Any]]:
        logger.info(f"Fetching prompt: {prompt_name} with tag: {tag or 'latest'}")
        # if self.use_cache:
        #     return self.fetch_from_cache(prompt_name)
        # else:
            # self.use_cache = True
        return self.fetch_from_cloud(prompt_name, tag)

    def fetch_from_cloud(self, prompt_name: str, tag: Optional[str] = "production") -> Optional[Dict[str, Any]]:
        if not self.langfuse_client:
            logger.error("Langfuse client not initialized, cannot fetch from cloud")

        try:
            logger.info(f"Fetching prompt '{prompt_name}' from Langfuse cloud with tag: {tag}")
            prompt = self.langfuse_client.get_prompt(name=prompt_name, label=tag)

            prompt_data = {
                "name": prompt_name,
                "tag": tag or "latest",
                "prompt": prompt.prompt,
                "config": prompt.config or {},
                "version": getattr(prompt, 'version', None),
                "labels": getattr(prompt, 'labels', []),
                "type": getattr(prompt, 'type', 'text'),
                "fetched_at": datetime.now().isoformat(),
                "cache_metadata": {
                    "source": "cloud",
                    "ttl_hours": self.cache_ttl.total_seconds() / 3600
                }
            }

            self._save_to_cache(prompt_name, prompt_data)

            logger.info(f"Successfully fetched and cached prompt '{prompt_name}'")
            return prompt_data

        except Exception as e:
            logger.error(f"Failed to fetch prompt '{prompt_name}' from cloud: {e}")
            logger.info("Attempting to fetch from cache as fallback")
            return self.fetch_from_cache(prompt_name)

    def fetch_from_cache(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        cache_file = self._get_cache_file_path(prompt_name)

        if not cache_file.exists():
            logger.warning(f"Cache file not found for prompt '{prompt_name}'")
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)

            # Check if cache is still valid
            if self._is_cache_valid(prompt_data):
                logger.info(f"Successfully fetched prompt '{prompt_name}' from cache")
                # Update metadata to indicate it came from cache
                prompt_data["cache_metadata"]["source"] = "cache"
                return prompt_data
            else:
                logger.warning(f"Cache expired for prompt '{prompt_name}'")
                # If we're in cache-only mode, return expired data with warning
                if self.use_cache:
                    logger.warning("Returning expired cache data as cache-only mode is enabled")
                    prompt_data["cache_metadata"]["expired"] = True
                    return prompt_data
                return None

        except Exception as e:
            logger.error(f"Failed to read cache file for prompt '{prompt_name}': {e}")
            return None

    def _save_to_cache(self, prompt_name: str, prompt_data: Dict[str, Any]) -> None:
        cache_file = self._get_cache_file_path(prompt_name)

        # try:
        #     cache_file.parent.mkdir(parents=True, exist_ok=True)

        #     with open(cache_file, 'w', encoding='utf-8') as f:
        #         json.dump(prompt_data, f, indent=2, ensure_ascii=False)

        #     logger.debug(f"Saved prompt '{prompt_name}' to cache: {cache_file}")

        # except Exception as e:
        #     logger.error(f"Failed to save prompt '{prompt_name}' to cache: {e}")

    def _get_cache_file_path(self, prompt_name: str) -> Path:
        """
        Generate cache file path maintaining the exact folder structure from prompt name.
        Example: 'test/try1/v1' -> 'cache/prompts/test/try1/v1.json'

        Tag is ignored for cache path as it doesn't affect caching.
        """
        # Split the prompt name by '/' to create folder structure
        parts = prompt_name.split('/')

        if len(parts) > 1:
            # Use all parts except the last as folder path
            folder_parts = parts[:-1]
            file_name = parts[-1]

            # Build the full folder path
            folder_path = self.cache_dir
            for part in folder_parts:
                folder_path = folder_path / part

            # Return the full path with the file (last part becomes filename.json)
            return folder_path / f"{file_name}.json"
        else:
            # No folder structure, save directly in cache root
            return self.cache_dir / f"{prompt_name}.json"

    def _is_cache_valid(self, prompt_data: Dict[str, Any]) -> bool:
        if "fetched_at" not in prompt_data:
            # No timestamp, consider invalid
            return False

        try:
            fetched_at = datetime.fromisoformat(prompt_data["fetched_at"])
            age = datetime.now() - fetched_at

            return age < self.cache_ttl

        except Exception as e:
            logger.error(f"Failed to validate cache timestamp: {e}")
            return False

    def clear_cache(self, prompt_name: Optional[str] = None, tag: Optional[str] = None) -> None:
        if prompt_name:
            cache_file = self._get_cache_file_path(prompt_name, tag)
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Cleared cache for prompt '{prompt_name}'")
            else:
                logger.warning(f"No cache found for prompt '{prompt_name}'")
        else:
            # Clear all cache files
            cache_files = list(self.cache_dir.glob("*.json"))
            for cache_file in cache_files:
                cache_file.unlink()
            logger.info(f"Cleared all {len(cache_files)} cached prompts")

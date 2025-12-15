#!/usr/bin/env python3
"""
Langfuse Prompt Fetcher Script

This script fetches all prompts from Langfuse and organizes them in a folder structure
that matches the Langfuse prompt organization. It creates individual files for each
prompt and a configuration file with metadata.

Usage:
    python scripts/utility/prompts/fetch_langfuse_prompts.py [--config CONFIG_FILE] [--output-dir OUTPUT_DIR]
"""

import os
import json
import argparse
import sys
import requests
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to Python path to allow imports from scripts/
# Script is now at scripts/utility/prompts/, so we need to go up 3 levels to reach project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langfuse import Langfuse
from scripts.utility.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
from scripts.logging_config import get_utility_logger

# Initialize logging
logger = get_utility_logger('fetch_langfuse_prompts')

class LangfusePromptFetcher:
    """Fetches and organizes prompts from Langfuse."""
    
    def __init__(self, output_dir: str = "prompts", max_depth: int = 10, create_folder_indexes: bool = False, folder_filter: Optional[str] = None, label: str = "latest"):
        """
        Initialize the prompt fetcher.

        Args:
            output_dir: Directory to save prompts to
            max_depth: Maximum folder depth to process
            create_folder_indexes: Create index.md files for folders
            folder_filter: Filter prompts by folder prefix (e.g. "Course-Creation-v2")
            label: Langfuse label to fetch (default: "latest")
        """
        self.output_dir = Path(output_dir)
        self.max_depth = max_depth
        self.create_folder_indexes = create_folder_indexes
        self.folder_filter = folder_filter
        self.label = label
        self.langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST
        )
        self.prompts_metadata = {}
        
        # Validate langfuse version for folder support
        try:
            import importlib.metadata
            langfuse_version = importlib.metadata.version('langfuse')
            try:
                from packaging import version
                if version.parse(langfuse_version) < version.parse('3.0.2'):
                    logger.warning(f"Langfuse version {langfuse_version} may not support folder features. Consider upgrading to >= 3.0.2")
            except ImportError:
                # Fallback for simple version comparison without packaging
                if tuple(map(int, langfuse_version.split('.')[:3])) < (3, 0, 2):
                    logger.warning(f"Langfuse version {langfuse_version} may not support folder features. Consider upgrading to >= 3.0.2")
        except Exception as e:
            logger.warning(f"Could not verify langfuse version: {e}")
        
    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string to be used as a filename.
        
        Args:
            name: The original name
            
        Returns:
            A sanitized filename
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Remove any trailing/leading spaces and dots
        name = name.strip('. ')
        
        # Ensure the name is not too long
        if len(name) > 200:
            name = name[:200]
            
        return name
    
    def create_folder_structure(self, prompt_name: str) -> Path:
        """
        Enhanced folder structure creation with proper nested support.
        Handles Langfuse's slash-based folder organization.
        
        Args:
            prompt_name: The name of the prompt
            
        Returns:
            Path to the folder where the prompt should be saved
        """
        # Normalize slashes and remove empty segments
        parts = [part.strip() for part in prompt_name.split('/') if part.strip()]
        
        if len(parts) <= 1:
            # No folder structure, save to root
            return self.output_dir
        
        # Check max depth limit
        folder_depth = len(parts) - 1
        if folder_depth > self.max_depth:
            logger.warning(f"Prompt '{prompt_name}' exceeds max depth {self.max_depth}, truncating to {self.max_depth} levels")
            parts = parts[:self.max_depth + 1]
        
        # Use all parts except the last one as folder hierarchy
        folder_parts = [self.sanitize_filename(part) for part in parts[:-1]]
        folder_path = self.output_dir
        
        # Create nested folder structure
        for i, folder_part in enumerate(folder_parts):
            folder_path = folder_path / folder_part
            folder_path.mkdir(exist_ok=True)
            
            # Create a folder metadata file if it doesn't exist
            self._create_folder_metadata(folder_path, folder_part, '/'.join(parts[:i+1]))
        
        return folder_path
    
    def _create_folder_metadata(self, folder_path: Path, folder_name: str, folder_hierarchy: str):
        """Create metadata file for folders to track organization"""
        metadata_file = folder_path / '.folder_info.json'
        
        if not metadata_file.exists():
            metadata = {
                'folder_name': folder_name,
                'folder_hierarchy': folder_hierarchy,
                'created_at': datetime.now().isoformat(),
                'description': f'Auto-generated folder for {folder_name} prompts',
                'prompts': [],
                'prompt_count': 0,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
    
    def _update_folder_metadata(self, folder_path: Path, filename: str, prompt_name: str):
        """Update folder metadata with new prompt"""
        metadata_file = folder_path / '.folder_info.json'
        
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {'prompts': []}
        
        # Add/update prompt entry
        prompt_entry = {
            'filename': filename,
            'full_name': prompt_name,
            'added_at': datetime.now().isoformat()
        }
        
        # Remove existing entry if present
        metadata['prompts'] = [p for p in metadata['prompts'] if p.get('filename') != filename]
        metadata['prompts'].append(prompt_entry)
        
        # Update folder metadata
        metadata['last_updated'] = datetime.now().isoformat()
        metadata['prompt_count'] = len(metadata['prompts'])
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def _is_valid_prompt_name(self, name: str) -> bool:
        """Validate if a string looks like a valid Langfuse prompt name"""
        # Basic validation for prompt names
        # Allow slashes for folder organization in Langfuse
        if not name or len(name.replace('/', '').strip()) < 1:
            return False
        
        # Should contain reasonable characters and not be too long
        if len(name) > 500:  # Increased limit for nested paths
            return False
        
        return True
    
    def _clean_prompt_name(self, name: str) -> str:
        """Clean up discovered prompt names by removing file extensions and normalizing"""
        if not name:
            return ""
        
        import re
        
        # Strip whitespace
        name = name.strip()
        
        # Remove common file extensions
        name = re.sub(r'\.(txt|json|py|md|js|ts)$', '', name, flags=re.IGNORECASE)
        
        # Remove config file suffixes  
        name = re.sub(r'_config$', '', name, flags=re.IGNORECASE)
        
        # Remove quotes if present
        name = name.strip('\'"')
        
        return name
    
    
    def save_prompt_file(self, prompt_data: Dict[str, Any], folder_path: Path) -> tuple[str, str]:
        """
        Enhanced prompt saving with better folder organization support.
        
        Args:
            prompt_data: The prompt data from Langfuse
            folder_path: The folder to save the prompt in
            
        Returns:
            Tuple of (prompt_filename, config_filename)
        """
        prompt_name = prompt_data['name']
        parts = prompt_name.split('/')
        filename = self.sanitize_filename(parts[-1])  # Use the last part as filename
        
        # Add .txt extension for prompt file
        prompt_file_path = folder_path / f"{filename}.txt"
        config_file_path = folder_path / f"{filename}_config.json"
        
        # Enhanced prompt content with folder context
        folder_hierarchy = ' > '.join(parts[:-1]) if len(parts) > 1 else 'Root'
        
        prompt_content = f"""# Prompt: {prompt_name}
            # Folder: {folder_hierarchy}
            # Version: {prompt_data.get('version', 'latest')}
            # Labels: {', '.join(prompt_data.get('labels', []))}
            # Created: {prompt_data.get('created_at', 'unknown')}
            # Updated: {prompt_data.get('updated_at', 'unknown')}
            # Type: {prompt_data.get('type', 'text')}
            # SDK Requirement: langfuse >= 3.0.2 (for folder support)
            #
            # --- PROMPT CONTENT ---

            {prompt_data.get('prompt', '')}
            """
        
        # Enhanced config with folder metadata
        config_content = {
            "prompt_name": prompt_name,
            "folder_hierarchy": parts[:-1] if len(parts) > 1 else [],
            "folder_path": folder_hierarchy,
            "filename": parts[-1],
            "version": prompt_data.get('version'),
            "labels": prompt_data.get('labels', []),
            "type": prompt_data.get('type', 'text'),
            "config": prompt_data.get('config', {}),
            "created_at": prompt_data.get('created_at'),
            "updated_at": prompt_data.get('updated_at'),
            "tags": prompt_data.get('tags', []),
            "fetch_timestamp": datetime.now().isoformat(),
            "sdk_requirement": "langfuse >= 3.0.2"
        }
        
        # Save prompt file
        with open(prompt_file_path, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
            
        # Save config file
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(config_content, f, indent=2, ensure_ascii=False)
        
        # Update folder metadata
        self._update_folder_metadata(folder_path, filename, prompt_name)
        
        logger.info(f"Saved prompt '{prompt_name}' to {prompt_file_path}")
        logger.info(f"Saved config for '{prompt_name}' to {config_file_path}")
        
        return prompt_file_path.name, config_file_path.name
    
    def fetch_all_prompts(self) -> List[Dict[str, Any]]:
        """Fetch all prompts from Langfuse."""
        
        logger.info("Fetching all prompts from Langfuse...")
        
        try:
            # Use REST API to fetch all prompts with pagination
            # Create basic auth header
            auth_string = f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/json'
            }
            
            all_prompts = []
            page = 1
            total_pages = 1
            
            while page <= total_pages:
                # Construct the API URL with pagination
                api_url = f"{LANGFUSE_HOST}/api/public/v2/prompts?limit=100&page={page}"
                
                response = requests.get(api_url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                raw_prompts = data.get('data', [])
                all_prompts.extend(raw_prompts)
                
                # Get pagination info
                meta = data.get('meta', {})
                total_pages = meta.get('totalPages', 1)
                total_items = meta.get('totalItems', len(raw_prompts))
                
                logger.info(f"Fetched page {page}/{total_pages} - {len(raw_prompts)} prompts on this page")
                page += 1
            
            logger.info(f"Found {len(all_prompts)} total prompts in Langfuse project across {total_pages} page(s)")
            raw_prompts = all_prompts
            
            processed_prompts = []
            for prompt_info in raw_prompts:
                try:
                    prompt_name = prompt_info.name if hasattr(prompt_info, 'name') else prompt_info.get('name', '')
                    
                    if not self._is_valid_prompt_name(prompt_name):
                        logger.debug(f"Skipping invalid prompt name: {prompt_name}")
                        continue
                    
                    # Apply folder filter if specified
                    if self.folder_filter and not prompt_name.startswith(self.folder_filter):
                        logger.debug(f"Skipping prompt '{prompt_name}' - doesn't match folder filter '{self.folder_filter}'")
                        continue
                    
                    logger.info(f"Fetching prompt: {prompt_name}")
                    
                    # Get the full prompt details
                    prompt = self.langfuse_client.get_prompt(name=prompt_name, label=self.label)
                    
                    prompt_dict = {
                        'name': prompt_name,
                        'version': getattr(prompt, 'version', None),
                        'prompt': getattr(prompt, 'prompt', ''),
                        'config': getattr(prompt, 'config', {}),
                        'labels': getattr(prompt, 'labels', []),
                        'type': getattr(prompt, 'type', 'text'),
                        'created_at': str(getattr(prompt, 'created_at', '')),
                        'updated_at': str(getattr(prompt, 'updated_at', '')),
                        'tags': getattr(prompt, 'tags', [])
                    }
                    processed_prompts.append(prompt_dict)
                    
                except Exception as prompt_error:
                    logger.warning(f"Could not fetch prompt '{prompt_name}': {prompt_error}")
                    continue
            
            if self.folder_filter:
                logger.info(f"Successfully fetched {len(processed_prompts)} prompts matching folder filter '{self.folder_filter}'")
            else:
                logger.info(f"Successfully fetched {len(processed_prompts)} prompts")
            return processed_prompts
            
        except Exception as e:
            logger.error(f"Failed to fetch prompts from Langfuse: {e}")
            return []
    
    def process_prompts(self, prompts: List[Dict[str, Any]]) -> None:
        """
        Process all prompts and save them to files with enhanced folder support.
        
        Args:
            prompts: List of prompt data from Langfuse
        """
        logger.info(f"Processing and saving {len(prompts)} prompts...")
        
        folder_stats = {}
        
        for prompt in prompts:
            try:
                prompt_name = prompt.get('name', 'unnamed_prompt')
                
                
                # Create folder structure
                folder_path = self.create_folder_structure(prompt_name)
                
                # Track folder statistics
                folder_key = str(folder_path.relative_to(self.output_dir))
                if folder_key not in folder_stats:
                    folder_stats[folder_key] = 0
                folder_stats[folder_key] += 1
                
                # Save the prompt file and config file
                prompt_filename, config_filename = self.save_prompt_file(prompt, folder_path)
                
                # Store metadata for summary
                self.prompts_metadata[prompt_name] = {
                    'prompt_file_path': str(Path(folder_path.relative_to(self.output_dir)) / prompt_filename),
                    'config_file_path': str(Path(folder_path.relative_to(self.output_dir)) / config_filename),
                    'folder_hierarchy': prompt_name.split('/')[:-1] if '/' in prompt_name else [],
                    'version': prompt.get('version'),
                    'labels': prompt.get('labels', []),
                    'type': prompt.get('type', 'text'),
                    'created_at': prompt.get('created_at'),
                    'updated_at': prompt.get('updated_at'),
                    'tags': prompt.get('tags', [])
                }
                
            except Exception as e:
                logger.error(f"Error processing prompt {prompt.get('name', 'unknown')}: {e}")
                continue
        
        # Create folder index files if requested
        if self.create_folder_indexes:
            self._create_folder_indexes(folder_stats)
        
        logger.info(f"Processing completed. Folders created: {len(folder_stats)}")
    
    def save_summary_file(self) -> None:
        """Save a summary file with fetch metadata and overview."""
        summary_data = {
            'fetch_timestamp': datetime.now().isoformat(),
            'total_prompts': len(self.prompts_metadata),
            'langfuse_host': LANGFUSE_HOST,
            'summary': 'Individual config files are saved next to each prompt file',
            'prompts_overview': {
                prompt_name: {
                    'prompt_file': metadata['prompt_file_path'],
                    'config_file': metadata['config_file_path'],
                    'version': metadata['version'],
                    'type': metadata['type']
                }
                for prompt_name, metadata in self.prompts_metadata.items()
            }
        }
        
        summary_path = self.output_dir / 'fetch_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved fetch summary to {summary_path}")
    
    def create_readme(self) -> None:
        """Create a README file explaining the structure."""
        readme_content = f"""# Langfuse Prompts Export

            This directory contains all prompts exported from Langfuse on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

            ## Structure

            - Each prompt is saved as a `.txt` file with simplified metadata header
            - Each prompt has a corresponding `_config.json` file with full configuration
            - Folder structure mirrors the Langfuse prompt organization
            - `fetch_summary.json` contains overview and fetch metadata

            ## Files

            Total prompts: {len(self.prompts_metadata)}

            ### Prompt Files by Category:

            """
        
        # Group prompts by top-level folder
        categories = {}
        for prompt_name, metadata in self.prompts_metadata.items():
            if '/' in prompt_name:
                category = prompt_name.split('/')[0]
            else:
                category = 'root'
            
            if category not in categories:
                categories[category] = []
            categories[category].append((
                prompt_name, 
                metadata['prompt_file_path'],
                metadata['config_file_path']
            ))
        
        for category, prompts in sorted(categories.items()):
            readme_content += f"\n#### {category}\n"
            for prompt_name, prompt_path, config_path in sorted(prompts):
                readme_content += f"- `{prompt_path}` + `{config_path}` - {prompt_name}\n"
        
        readme_content += f"""

            ## Usage

            To use these prompts in your application:

            1. **Prompt Content**: Read from `.txt` files for the actual prompt text
            2. **Configuration**: Use corresponding `_config.json` files for:
            - Model settings (temperature, max_tokens, etc.)
            - Output schemas and validation rules
            - Version information and labels
            - Creation/update timestamps

            3. **Folder Structure**: Matches the Langfuse organization for easy navigation

            ## Configuration Files

            Each prompt has its own config file with:
            - Full Langfuse configuration (model, temperature, etc.)
            - Output schema (if structured output is required)
            - Version and label information
            - Fetch timestamp for tracking

            ## Example Usage

            ```python
            import json

            # Load prompt content
            with open('Course-Creation/Course/Creation-Prompt.txt', 'r') as f:
                prompt_text = f.read()

            # Load configuration
            with open('Course-Creation/Course/Creation-Prompt_config.json', 'r') as f:
                config = json.load(f)
    
            # Use the configuration
            model = config['config']['model']
            temperature = config['config']['temperature']
            output_schema = config['config'].get('output_schema')
            ```
            """
        
        readme_path = self.output_dir / 'README.md'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"Created README file at {readme_path}")
    
    def run(self) -> None:
        """Main execution method."""
        if self.folder_filter:
            logger.info(f"Starting Langfuse prompt fetch to directory: {self.output_dir} (filtering by folder: {self.folder_filter})")
        else:
            logger.info(f"Starting Langfuse prompt fetch to directory: {self.output_dir}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Fetch all prompts
        prompts = self.fetch_all_prompts()
        
        # Process and save prompts
        self.process_prompts(prompts)
        
        # Save summary file
        self.save_summary_file()
        
        # Create README
        self.create_readme()
        
        logger.info(f"Successfully fetched and saved {len(self.prompts_metadata)} prompts")
        print(f"✅ Fetched {len(self.prompts_metadata)} prompts to {self.output_dir}")
        print(f"📁 Check {self.output_dir}/README.md for details")


    def _create_folder_indexes(self, folder_stats: Dict[str, int]) -> None:
        """Create index.md files for folders"""
        logger.info("Creating folder index files...")
        
        for folder_path_str, count in folder_stats.items():
            if folder_path_str == '.':
                continue  # Skip root folder
                
            folder_path = self.output_dir / folder_path_str
            index_file = folder_path / 'index.md'
            
            folder_name = folder_path.name
            parent_folders = ' > '.join(folder_path.relative_to(self.output_dir).parts[:-1])
            
            index_content = f"""# {folder_name} Prompts

                Folder: {parent_folders + ' > ' if parent_folders else ''}{folder_name}
                Prompts in this folder: {count}

                ## Available Prompts

                """
            
            # List prompts in this folder
            for prompt_name, metadata in self.prompts_metadata.items():
                if metadata['prompt_file_path'].startswith(folder_path_str):
                    relative_prompt_path = metadata['prompt_file_path'].replace(folder_path_str + '/', '')
                    if '/' not in relative_prompt_path:  # Direct child, not nested
                        index_content += f"- [{relative_prompt_path}]({relative_prompt_path}) - {prompt_name}\n"
            
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(index_content)
            
            logger.info(f"Created index file: {index_file}")

def main():
    """Main function with enhanced CLI argument parsing."""
    parser = argparse.ArgumentParser( description="Fetch all prompts from Langfuse with nested folder support")
    parser.add_argument( '--output-dir', default='prompts', help='Output directory for prompt files (default: prompts)')
    parser.add_argument( '--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument( '--max-depth', type=int, default=100, help='Maximum folder depth to process (default: 100)')
    parser.add_argument( '--create-index', action='store_true', help='Create an index.md file for each folder')
    parser.add_argument( '--folder-filter', help='Filter prompts by folder prefix (e.g. "Course-Creation-v2")')
    parser.add_argument( '--label', default='latest', help='Langfuse label to fetch (default: latest)')
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    try:
        # Create fetcher
        fetcher = LangfusePromptFetcher(
            output_dir=args.output_dir,
            max_depth=args.max_depth,
            create_folder_indexes=args.create_index,
            folder_filter=args.folder_filter,
            label=args.label
        )
        fetcher.run()
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
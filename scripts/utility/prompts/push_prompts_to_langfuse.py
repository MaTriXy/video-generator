#!/usr/bin/env python3
"""
Langfuse Prompt Uploader Script

This script uploads all prompts from the local prompts/ folder to Langfuse as new versions.
It's the reverse operation of fetch_langfuse_prompts.py.

Usage:
    python scripts/utility/prompts/push_prompts_to_langfuse.py [--prompts-dir PROMPTS_DIR] [--dry-run] [--force]
"""

import os
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from langfuse import Langfuse
from scripts.utility.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
from scripts.logging_config import get_utility_logger

# Initialize logging
logger = get_utility_logger('push_prompts_to_langfuse')

class LangfusePromptUploader:
    """Uploads local prompts to Langfuse as new versions."""
    
    def __init__(self, prompts_dir: str = "prompts", dry_run: bool = False):
        """
        Initialize the prompt uploader.
        
        Args:
            prompts_dir: Directory containing the prompts to upload
            dry_run: If True, only show what would be uploaded without actually doing it
        """
        self.prompts_dir = Path(prompts_dir)
        self.dry_run = dry_run
        self.langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST
        )
        self.upload_results = {
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
    def discover_prompt_files(self) -> List[Tuple[Path, Path]]:
        """
        Discover all prompt files and their corresponding config files.
        
        Returns:
            List of tuples (prompt_file_path, config_file_path)
        """
        logger.info(f"Discovering prompt files in {self.prompts_dir}")
        
        prompt_files = []
        
        # Find all .txt files (excluding README.md)
        for txt_file in self.prompts_dir.rglob("*.txt"):
            if txt_file.name == "README.md":
                continue
                
            # Look for corresponding config file
            config_file = txt_file.with_name(f"{txt_file.stem}_config.json")
            
            if config_file.exists():
                prompt_files.append((txt_file, config_file))
                logger.info(f"Found prompt pair: {txt_file.name} + {config_file.name}")
            else:
                logger.warning(f"No config file found for {txt_file}, skipping")
        
        logger.info(f"Discovered {len(prompt_files)} prompt files with configs")
        return prompt_files
    
    def parse_prompt_file(self, prompt_file: Path) -> Dict[str, Any]:
        """
        Parse a prompt file to extract metadata and content.
        
        Args:
            prompt_file: Path to the prompt file
            
        Returns:
            Dictionary with prompt metadata and content
        """
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the header metadata
        metadata = {}
        lines = content.split('\n')
        
        # Extract metadata from header comments
        for line in lines:
            if line == '# --- PROMPT CONTENT ---':
                # Start of actual content
                content_start_idx = lines.index(line) + 1
                break
            elif line.startswith('#'):
                if ': ' in line:
                    key_part = line.split(': ', 1)[0].replace('# ', '').lower().replace(' ', '_')
                    value_part = line.split(': ', 1)[1]
                    
                    if key_part == 'prompt':
                        metadata['name'] = value_part
                    elif key_part == 'version':
                        metadata['version'] = value_part
                    elif key_part == 'labels':
                        metadata['labels'] = [label.strip() for label in value_part.split(',')]
                    elif key_part == 'type':
                        metadata['type'] = value_part
        else:
            # No content marker found, assume all non-comment lines are content
            content_start_idx = 0
            for i, line in enumerate(lines):
                if not line.startswith('#') and line.strip():
                    content_start_idx = i
                    break
        
        # Extract the actual prompt content
        prompt_content = '\n'.join(lines[content_start_idx:]).strip()
        
        metadata['prompt_content'] = prompt_content
        
        return metadata
    
    def load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """
        Load configuration from the config file.
        
        Args:
            config_file: Path to the config file
            
        Returns:
            Configuration dictionary
        """
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        return config_data
    
    def construct_prompt_name(self, prompt_file: Path, config_data: Dict[str, Any]) -> str:
        """
        Construct the full prompt name from file path and config.
        
        Args:
            prompt_file: Path to the prompt file
            config_data: Configuration data
            
        Returns:
            Full prompt name for Langfuse
        """
        # First try to get name from config
        if 'prompt_name' in config_data and config_data['prompt_name']:
            return config_data['prompt_name']
        
        # Fallback: construct from file path
        relative_path = prompt_file.relative_to(self.prompts_dir)
        
        # Convert file path to prompt name (remove .txt extension)
        path_parts = list(relative_path.parts[:-1])  # All parts except filename
        filename = relative_path.stem  # Filename without extension
        path_parts.append(filename)
        
        prompt_name = '/'.join(path_parts)
        return prompt_name
    
    def upload_prompt_to_langfuse(self, prompt_name: str, prompt_content: str, 
                                 config: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
        """
        Upload a single prompt to Langfuse.
        
        Args:
            prompt_name: Name of the prompt in Langfuse
            prompt_content: The actual prompt content
            config: Configuration dictionary
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Uploading prompt: {prompt_name}")
            
            if self.dry_run:
                print(f"[DRY RUN] Would upload prompt: {prompt_name}")
                print(f"          Content length: {len(prompt_content)} characters")
                print(f"          Config keys: {list(config.get('config', {}).keys())}")
                return True
            
            # Prepare the upload data
            upload_data = {
                'name': prompt_name,
                'prompt': prompt_content,
                'labels': metadata.get('labels', ['latest']),
                'tags': metadata.get('tags', [])
            }
            
            # Add configuration if available
            if 'config' in config and config['config']:
                upload_data['config'] = config['config']
            
            # Upload to Langfuse using create_prompt
            response = self.langfuse_client.create_prompt(**upload_data)
            
            logger.info(f"✅ Successfully uploaded: {prompt_name}")
            print(f"✅ Uploaded: {prompt_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {prompt_name}: {e}")
            print(f"❌ Failed: {prompt_name} - {e}")
            return False
    
    def process_all_prompts(self, force: bool = False) -> None:
        """
        Process all discovered prompts and upload them to Langfuse.
        
        Args:
            force: If True, upload even if prompt already exists
        """
        prompt_files = self.discover_prompt_files()
        
        if not prompt_files:
            logger.warning("No prompt files found!")
            print("⚠️  No prompt files found in the prompts directory")
            return
        
        print(f"\n📤 {'[DRY RUN] ' if self.dry_run else ''}Uploading {len(prompt_files)} prompts to Langfuse...")
        print(f"🌐 Target: {LANGFUSE_HOST}")
        print()
        
        for i, (prompt_file, config_file) in enumerate(prompt_files, 1):
            try:
                print(f"[{i}/{len(prompt_files)}] Processing: {prompt_file.name}")
                
                # Parse prompt file
                prompt_metadata = self.parse_prompt_file(prompt_file)
                
                # Load config file
                config_data = self.load_config_file(config_file)
                
                # Construct prompt name
                prompt_name = self.construct_prompt_name(prompt_file, config_data)
                
                # Get prompt content
                prompt_content = prompt_metadata['prompt_content']
                
                # Upload to Langfuse
                success = self.upload_prompt_to_langfuse(
                    prompt_name, 
                    prompt_content, 
                    config_data, 
                    prompt_metadata
                )
                
                if success:
                    self.upload_results['successful'].append({
                        'prompt_name': prompt_name,
                        'file_path': str(prompt_file),
                        'content_length': len(prompt_content)
                    })
                else:
                    self.upload_results['failed'].append({
                        'prompt_name': prompt_name,
                        'file_path': str(prompt_file),
                        'error': 'Upload failed'
                    })
                
            except Exception as e:
                logger.error(f"Error processing {prompt_file}: {e}")
                self.upload_results['failed'].append({
                    'prompt_name': str(prompt_file),
                    'file_path': str(prompt_file),
                    'error': str(e)
                })
                print(f"❌ Error processing {prompt_file.name}: {e}")
                continue
    
    def print_summary(self) -> None:
        """Print upload summary."""
        successful = len(self.upload_results['successful'])
        failed = len(self.upload_results['failed'])
        total = successful + failed
        
        print(f"\n{'='*60}")
        print(f"📊 {'DRY RUN ' if self.dry_run else ''}UPLOAD SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Total: {total}")
        
        if self.upload_results['successful']:
            print(f"\n✅ Successfully {'processed' if self.dry_run else 'uploaded'}:")
            for result in self.upload_results['successful']:
                print(f"   • {result['prompt_name']} ({result['content_length']} chars)")
        
        if self.upload_results['failed']:
            print(f"\n❌ Failed:")
            for result in self.upload_results['failed']:
                print(f"   • {result['prompt_name']}: {result['error']}")
        
        if self.dry_run:
            print(f"\n💡 This was a dry run. Use --no-dry-run to actually upload the prompts.")
        else:
            print(f"\n🎉 Upload complete! Check your Langfuse dashboard to verify.")
    
    def run(self, force: bool = False) -> None:
        """Main execution method."""
        logger.info(f"Starting prompt upload from {self.prompts_dir}")
        
        if not self.prompts_dir.exists():
            print(f"❌ Prompts directory not found: {self.prompts_dir}")
            return
        
        # Process all prompts
        self.process_all_prompts(force=force)
        
        # Print summary
        self.print_summary()


def main():
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Upload local prompts to Langfuse as new versions"
    )
    
    parser.add_argument(
        '--prompts-dir',
        default='prompts',
        help='Directory containing prompt files (default: prompts)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Show what would be uploaded without actually uploading (default: True)'
    )
    
    parser.add_argument(
        '--no-dry-run',
        action='store_true',
        help='Actually upload the prompts (overrides --dry-run)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Upload even if prompt already exists'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    # Determine if this is a dry run
    dry_run = args.dry_run and not args.no_dry_run
    
    try:
        # Create uploader and run
        uploader = LangfusePromptUploader(
            prompts_dir=args.prompts_dir,
            dry_run=dry_run
        )
        uploader.run(force=args.force)
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
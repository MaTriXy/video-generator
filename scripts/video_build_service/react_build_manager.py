"""
ReactBuildManager for building TSX components into UMD bundles.
Standalone version for video build service.
"""

import os
import sys
import shutil
import subprocess
import logging
from time import sleep
from typing import Dict, Any, Optional
from pathlib import Path
from .tsx_build_env_controller import TsxBuildEnvController

logger = logging.getLogger('react_build_manager')


class ReactBuildManager:
    """Manager for building React components from TSX files."""

    def __init__(self, project_root: Path = None):
        """Initialize the React Build Manager."""
        self.env_controller = TsxBuildEnvController(project_root)
        self.build_env_path = None
        self.src_path = None
        self.dist_path = None

    def prepare_component_source(self, tsx_path: str) -> bool:
        """
        Copy TSX file to TsxBuildEnv/src directory and add CSS import.
        Also copies all scene component files from the same directory.
        """
        try:
            if not self.src_path:
                logger.error("Build environment not initialized")
                return False

            target_path = self.src_path / "video.tsx"

            with open(tsx_path, 'r', encoding='utf-8') as f:
                tsx_content = f.read()

            if '../index.css' not in tsx_content:
                tsx_content = 'import "../index.css";\n' + tsx_content

            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(tsx_content)

            logger.info(f"Copied TSX to {target_path}")

            # Copy all scene component files from the same directory
            source_dir = Path(tsx_path).parent
            scene_files_copied = self._copy_scene_components(source_dir)

            if scene_files_copied > 0:
                logger.info(f"Copied {scene_files_copied} scene component files")

            return True

        except Exception as e:
            logger.error(f"Error preparing TSX component: {e}")
            return False

    def _copy_scene_components(self, source_dir: Path) -> int:
        """Copy all scene component files from source directory to TsxBuildEnv/src."""
        try:
            if not self.src_path:
                return 0

            # Find scene files with pattern scene_*.tsx
            scene_files = list(source_dir.glob("scene_*.tsx"))

            copied_count = 0
            for scene_file in scene_files:
                target_file = self.src_path / scene_file.name
                shutil.copy2(scene_file, target_file)
                copied_count += 1

            return copied_count

        except Exception as e:
            logger.error(f"Error copying scene components: {e}")
            return 0

    def execute_build(self) -> bool:
        """Execute Vite build in TsxBuildEnv."""
        try:
            if not self.build_env_path:
                logger.error("Build environment not initialized")
                return False

            is_windows = sys.platform == 'win32'

            env = os.environ.copy()
            env['COMPONENT'] = 'video'

            result = subprocess.run(
                "npm run build:video" if is_windows else ["npm", "run", "build:video"],
                cwd=str(self.build_env_path),
                capture_output=True,
                text=True,
                shell=is_windows,
                env=env,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"Build failed: {result.stderr}")
                logger.error(f"Build stdout: {result.stdout}")
                return False

            return True

        except subprocess.TimeoutExpired:
            logger.error("Build timed out")
            return False
        except Exception as e:
            logger.error(f"Error building component: {e}")
            return False

    def get_built_file_path(self) -> Optional[str]:
        """Get the path to the built JS file in TsxBuildEnv/dist."""
        try:
            if not self.dist_path:
                logger.error("Build environment not initialized")
                return None

            js_files = list(self.dist_path.glob("*.js"))

            if not js_files:
                js_files = list(self.dist_path.glob("*/*.js"))

            if js_files:
                built_file = js_files[0]
                return str(built_file)

            logger.error("No built JS file found in dist folder")
            return None

        except Exception as e:
            logger.error(f"Error finding built file: {e}")
            return None

    def clean_src_folder(self) -> None:
        """Clean the src folder in TsxBuildEnv after build."""
        try:
            if self.src_path and self.src_path.exists():
                video_file = self.src_path / "video.tsx"
                if video_file.exists():
                    video_file.unlink()

                # Remove all scene component files
                scene_files = list(self.src_path.glob("scene_*.tsx"))
                for scene_file in scene_files:
                    scene_file.unlink()

        except Exception as e:
            logger.warning(f"Error cleaning src folder: {e}")

    def build_component(self, tsx_path: str) -> Dict[str, Any]:
        """
        Build React component from TSX file using TsxBuildEnv.

        Returns:
            Dict with success, built_path, and errors
        """
        if not os.path.exists(tsx_path):
            return {
                'success': False,
                'built_path': None,
                'errors': [f'TSX file not found: {tsx_path}']
            }

        errors = []

        try:
            if not self.env_controller.ensure_build_env_exists():
                errors.append("Failed to setup TsxBuildEnv")
                return {
                    'success': False,
                    'built_path': None,
                    'errors': errors
                }

            self.build_env_path = self.env_controller.get_build_env_path()
            self.src_path = self.env_controller.get_src_path()
            self.dist_path = self.env_controller.get_dist_path()

            if not self.prepare_component_source(tsx_path):
                errors.append("Failed to prepare component source")
                return {
                    'success': False,
                    'built_path': None,
                    'errors': errors
                }
            sleep(1)

            if not self.execute_build():
                errors.append("Failed to build component")
                return {
                    'success': False,
                    'built_path': None,
                    'errors': errors
                }

            built_path = self.get_built_file_path()

            if not built_path:
                errors.append("Failed to find built output")
                return {
                    'success': False,
                    'built_path': None,
                    'errors': errors
                }

            self.clean_src_folder()

            return {
                'success': True,
                'built_path': built_path,
                'errors': []
            }

        except Exception as e:
            logger.error(f"Unexpected error during build: {e}")
            errors.append(str(e))
            return {
                'success': False,
                'built_path': None,
                'errors': errors
            }

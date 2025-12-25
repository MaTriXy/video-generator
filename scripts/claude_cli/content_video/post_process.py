import json
import sys
import os
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path



# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from scripts.utility.config import AWS_ACCESS_KEY_ID
from scripts.logging_config import set_console_logging
from scripts.video_build_service.build_and_upload import BuildAndUploadService
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.enums import AssetType
from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController


BASE_IMPORTS = """import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const fontStyles = `
  @font-face {
    font-family: 'TextFontFamily';
    src: url('{text_font_url}') format('{font_format}');
    font-weight: normal;
    font-style: normal;
  }

  .video-container,
  .video-container * {
    font-family: 'TextFontFamily', sans-serif !important;
  }
`;

/**
 * Path Following Utilities
 * Shared across all scenes for animating elements along SVG paths
 */
const getPathPoint = (
  pathD: string,
  progress: number,
  elementOrientation: number
): { x: number; y: number; rotation: number } => {
  if (typeof document === 'undefined') {
    return { x: 0, y: 0, rotation: 0 };
  }

  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', pathD);
  const totalLength = path.getTotalLength();
  const point = path.getPointAtLength(totalLength * Math.min(progress, 1));

  // Calculate path direction from tangent
  // Using atan2(dx, -dy) gives 0°=UP directly (positive=clockwise)
  const delta = 1;
  const point1 = path.getPointAtLength(Math.max(0, totalLength * progress - delta));
  const point2 = path.getPointAtLength(Math.min(totalLength, totalLength * progress + delta));
  const pathAngle = Math.atan2(point2.x - point1.x, point1.y - point2.y) * (180 / Math.PI);

  // Calculate rotation needed to align element with path
  const rotation = pathAngle - elementOrientation;

  return { x: point.x, y: point.y, rotation };
};
"""

SCENE_IMPORT_TEMPLATE = "import Scene{scene_index} from './scene_{scene_index}.tsx';"

VIDEO_PLAYER_INTERFACE = """interface VideoPlayerProps {
  currentTime: number;
  onScenesSetUp?: (scenes: Array<{start: number, end: number}>) => void;
  onSceneChange?: (sceneIndex: number) => void;
}"""

VIDEO_PLAYER_FUNCTION_START = """const VideoPlayer = ({ currentTime, onScenesSetUp, onSceneChange }: VideoPlayerProps) => {
  const [currentSceneIndex, setCurrentSceneIndex] = useState(-1);

  const scenes = ["""

VIDEO_PLAYER_SCENE_ENTRY = """    {{ start: {start_time}, end: {end_time}, Component: Scene{scene_index}}}"""

VIDEO_PLAYER_FUNCTION_END = """  ];

  // Setup scenes when component mounts or scenes change
  useEffect(() => {
    if (onScenesSetUp && scenes.length > 0) {
      onScenesSetUp(scenes);
    }
  }, []);

  // Update current scene based on time
  useEffect(() => {
    const activeScene = scenes.findIndex(
      scene => currentTime >= scene.start && currentTime < scene.end
    );
    if (activeScene !== -1 && activeScene !== currentSceneIndex) {
      setCurrentSceneIndex(activeScene);
      if (onSceneChange) {
        onSceneChange(activeScene);
      }
    }
  }, [currentTime, currentSceneIndex]);
  const SceneComponent = useMemo(() => {
    if (currentSceneIndex < 0 || currentSceneIndex >= scenes.length) {
      return null;
    }
    return scenes[currentSceneIndex].Component;
  }, [currentSceneIndex]);
  return (
    <div className="video-container relative w-full h-full bg-slate-900 overflow-hidden">
      <style dangerouslySetInnerHTML={{ __html: fontStyles }} />
      {/* Render only the currently active scene */}
      {currentSceneIndex >= 0 && currentSceneIndex < scenes.length && (
        <SceneComponent
          currentTime={currentTime}
          getPathPoint={getPathPoint}
        />
      )}
    </div>
  );
}
export default VideoPlayer;
"""


class VideoContentPostProcessing(BasePostProcess):
    """
    Post-processing for React video component generation.
    Extends BasePostProcess with specialized scene combination logic.
    """

    def __init__(self, topic: str):
        super().__init__(
            logger_name='ContentVideoPostProcessing',
            log_file_name='content-video-post-process',
            topic=topic,
            asset_type=AssetType.VIDEO,
        )
        self.deployService = BuildAndUploadService(topic=topic)
        self.claude_cli_scene_output_path = self.claude_cli_config.get_latest_path(self.asset_type)
        self.metadata_controller = VideoStepMetadataController()


    @try_catch
    def copy_scene_files_to_version_dir(self, version_dir: Path) -> bool:
        """Copy scene files to the version directory."""
        self.logger.info(f"Copying scene files to {version_dir}")

        # Get base directory from the latest path
        latest_path = self.claude_cli_config.get_latest_path(self.asset_type)
        base_dir = Path(latest_path).parent
        pattern = "scene_[0-9]*.tsx"
        scene_files = list(base_dir.glob(pattern))

        if not scene_files:
            self.logger.warning(f"No scene files found matching pattern: {pattern}")
            return False

        self.logger.info(f"Found {len(scene_files)} scene files to copy")

        copied_count = 0
        for scene_file in scene_files:
            try:
                dest_file = version_dir / scene_file.name
                self.logger.info(f"Copying {scene_file.name} to {dest_file}")
                dest_file.write_text(scene_file.read_text(encoding='utf-8'), encoding='utf-8')
                self.logger.info(f" Copied {scene_file.name} to version directory")
                copied_count += 1
            except Exception as e:
                self.logger.error(f"Failed to copy {scene_file.name}: {str(e)}")

        self.logger.info(f" Successfully copied {copied_count}/{len(scene_files)} scene files to {version_dir}")
        return copied_count == len(scene_files)

    def generate_video_player_with_imports(self, scenes_data: list) -> str:
        """Generate VideoPlayer component with scene imports."""
        content_parts = []

        # Add base imports
        video_style = self.manifest_controller.get_metadata().get('video_style', '')
        font_style = ClaudeCliConfig.FONT_URLS[video_style]
        content_parts.append(BASE_IMPORTS.replace("{text_font_url}", font_style["url"]).replace("{font_format}", font_style["format"]))
        content_parts.append("")

        # Add comment for scene imports
        content_parts.append("// Import all scene components")

        # Add scene imports
        for scene in scenes_data:
            scene_import = SCENE_IMPORT_TEMPLATE.format(
                scene_index=scene['index']
            )
            content_parts.append(scene_import)

        content_parts.append("")

        # Add VideoPlayer interface
        content_parts.append(VIDEO_PLAYER_INTERFACE)
        content_parts.append("")

        # Add VideoPlayer function start
        content_parts.append(VIDEO_PLAYER_FUNCTION_START)

        # Add scene entries
        for i, scene in enumerate(scenes_data):
            # First scene should start at 10 instead of 0
            start_time = 10 if i == 0 else scene['start_time']

            scene_entry = VIDEO_PLAYER_SCENE_ENTRY.format(
                start_time=start_time,
                end_time=scene['end_time'],
                scene_index=scene['index'],
            )

            # Add comma if not the last scene
            if i < len(scenes_data) - 1:
                scene_entry += ","

            content_parts.append(scene_entry)

        # Add VideoPlayer function end
        content_parts.append(VIDEO_PLAYER_FUNCTION_END)
        content_parts.append("")

        return '\n'.join(content_parts)

    @try_catch
    def combine_scene_files(self) -> Optional[str]:
        """Combine all scene files into a single VideoPlayer component."""
        self.logger.info("Combining scene files")

        direction_data = self.output_controller.read_output(AssetType.DIRECTION)
        if not direction_data:
            self.logger.error("Could not read direction file")
            return None

        scenes = direction_data.get('scenes', [])
        if not scenes:
            self.logger.error("No scenes found in direction file")
            return None

        self.logger.info(f"Found {len(scenes)} scenes in direction file")

        # Collect all scene components
        scene_components = []
        scene_imports = set()

        for scene_index, scene_data in enumerate(scenes):
            scene_file_path = self.claude_cli_scene_output_path.format(
                scene_index=scene_index
            )

            try:
                scene_content = self.file_io.read_text(scene_file_path)
                if not scene_content:
                    self.logger.warning(f"Could not read scene file: {scene_file_path}")
                    continue

                # Extract imports and component code
                lines = scene_content.split('\n')
                component_start = -1

                # Find where imports end and component starts
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    # Collect unique imports
                    if stripped.startswith('import '):
                        scene_imports.add(line)
                    # Find the interface or function definition
                    elif stripped.startswith('interface ') or stripped.startswith('export default function'):
                        component_start = i
                        break

                if component_start == -1:
                    self.logger.warning(f"Could not find component start in {scene_file_path}")
                    continue

                # Extract component code (from interface to end)
                component_code = '\n'.join(lines[component_start:])

                # Remove the 'export default' from the function definition
                component_code = component_code.replace('export default function', 'function')

                scene_components.append({
                    'index': scene_index,
                    'code': component_code,
                    'start_time': scene_data.get('sceneStartTime') or scene_data.get('startTime', 0),
                    'end_time': scene_data.get('sceneEndTime') or scene_data.get('endTime', 0),
                })

                self.logger.info(f"Extracted Scene{scene_index} component")

            except Exception as e:
                self.logger.error(f"Error processing scene {scene_index}: {str(e)}")
                continue

        if not scene_components:
            self.logger.error("No scene components were extracted")
            return None

        # Build the combined file
        combined_content = self._build_combined_tsx(scene_components, sorted(scene_imports))

        self.logger.info(f"Successfully combined {len(scene_components)} scenes into single file")
        return combined_content

    def _consolidate_imports(self, imports: list) -> list:
        """Consolidate imports from the same module into single import statements."""
        import re

        # Dictionary to store imports by module: {module: set(items)}
        imports_by_module = {}

        for imp in imports:
            # Skip React and framer-motion imports (already handled)
            if 'from \'react\'' in imp.lower() or 'from "react"' in imp.lower() or 'framer-motion' in imp.lower():
                continue

            # Parse import statement: import { X, Y } from 'module'
            match = re.match(r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]', imp)
            if match:
                items_str = match.group(1)
                module = match.group(2)

                # Extract individual items
                items = [item.strip() for item in items_str.split(',')]

                # Add to module's import set
                if module not in imports_by_module:
                    imports_by_module[module] = set()
                imports_by_module[module].update(items)

        # Build consolidated import statements
        consolidated = []
        for module in sorted(imports_by_module.keys()):
            items = sorted(imports_by_module[module])
            consolidated.append(f"import {{ {', '.join(items)} }} from '{module}';")

        return consolidated

    def _build_combined_tsx(self, scene_components: list, imports: list) -> str:
        """Build the combined TSX file content."""
        # Start with standard imports
        content_parts = [
            "import React, { useState, useEffect } from 'react';",
            "import { motion, AnimatePresence } from 'framer-motion';"
        ]

        # Consolidate and add unique imports from scenes
        consolidated_imports = self._consolidate_imports(imports)
        content_parts.extend(consolidated_imports)

        content_parts.append("")  # Blank line

        # Add all scene components
        for scene in scene_components:
            content_parts.append(scene['code'])
            content_parts.append("")  # Blank line between components

        # Add VideoPlayer interface and component
        content_parts.extend([
            "interface VideoPlayerProps {",
            "  currentTime: number;",
            "}",
            "",
            "const VideoPlayer = ({ currentTime }: VideoPlayerProps) => {",
            "  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);",
            "",
            "  // Define all scenes with their time ranges and components",
            "  const scenes = ["
        ])

        # Add scenes array entries
        for i, scene in enumerate(scene_components):
            comma = "," if i < len(scene_components) - 1 else ""
            content_parts.append(
                f"    {{ start: {scene['start_time']}, end: {scene['end_time']}, Component: Scene{scene['index']} }}{comma}"
            )

        content_parts.extend([
            "  ];",
            "",
            "  // Update current scene based on time",
            "  useEffect(() => {",
            "    const activeScene = scenes.findIndex(",
            "      scene => currentTime >= scene.start && currentTime < scene.end",
            "    );",
            "    if (activeScene !== -1 && activeScene !== currentSceneIndex) {",
            "      setCurrentSceneIndex(activeScene);",
            "    }",
            "  }, [currentTime, currentSceneIndex]);",
            "",
            "  return (",
            "    <div className=\"relative w-full h-full bg-slate-900 overflow-hidden\">",
            "      {/* Render only the currently active scene */}",
            "      {currentSceneIndex >= 0 && currentSceneIndex < scenes.length && (",
            "        <scenes[currentSceneIndex].Component currentTime={currentTime - scenes[currentSceneIndex].start} />",
            "      )}",
            "    </div>",
            "  );",
            "}",
            "",
            "export default VideoPlayer;"
        ])

        return '\n'.join(content_parts)

    @try_catch
    def generate_from_direction_file(self) -> Optional[str]:
        self.logger.info("Generating VideoPlayer from direction file")

        direction_data = self.output_controller.read_output(AssetType.DIRECTION)
        max_scenes = self.metadata_controller.get_total_scenes(self.asset_type)
        if not direction_data:
            self.logger.error("Could not read direction file")
            return None

        scenes = direction_data.get('scenes', [])
        scenes_data = []
        for scene_index, scene in enumerate(scenes):
            if scene_index >= max_scenes:
                break
            scenes_data.append({
                'index': scene_index,
                'start_time': scene.get('sceneStartTime') or scene.get('startTime', 0),
                'end_time': scene.get('sceneEndTime') or scene.get('endTime', 0)
            })

        self.logger.info(f"----> Found {len(scenes_data)} scenes in direction file")

        # Generate VideoPlayer component
        video_player_content = self.generate_video_player_with_imports(
            scenes_data=scenes_data
        )

        self.logger.info(f"Successfully generated VideoPlayer component with {len(scenes_data)} scene imports")
        return video_player_content

    # ==================== Base Class Method Implementations ====================

    @try_catch
    def process_output(self) -> Tuple[Optional[str], Optional[str]]:
        """Process video output and write versioned output."""
        self.logger.info("Processing video output")
        file_path, version = self.write_versioned_output()

        if file_path and version:
            # Copy scene files to version directory
            self.copy_scene_files_to_version_dir(Path(file_path).parent)

        self.logger.info("Video output processed successfully")
        return version, file_path

    @try_catch
    def process(self) -> Tuple[bool, Optional[str]]:
        """Complete processing workflow."""
        version, file_path = self.process_output()

        if not version or not file_path:
            self.logger.error("Failed to process video output")
            return False, None

        return True, file_path

    # ==================== Additional Workflow Methods ====================

    @try_catch
    def combine_and_save_scenes(self) -> Tuple[bool, Optional[str]]:
        """Combine all scene files and save."""
        # Combine all scene files
        combined_content = self.combine_scene_files()

        if not combined_content:
            self.logger.error("Failed to combine scene files")
            return False, None

        # Save the combined file to latest path
        latest_path = self.claude_cli_config.get_latest_path(self.asset_type)

        try:
            self.file_io.write_text(latest_path, combined_content)
            self.logger.info(f" Combined video file saved: {latest_path}")
            file_path, version = self.write_versioned_output()
            return True, latest_path
        except Exception as e:
            self.logger.error(f"Failed to save combined file: {str(e)}")
            return False, None

    @try_catch
    def generate_and_save_from_direction(self) -> Tuple[bool, Optional[str]]:
        video_player_content = self.generate_from_direction_file()

        if not video_player_content:
            self.logger.error("Failed to generate VideoPlayer from direction file")
            return False, None

        # Save the VideoPlayer file to latest path
        latest_path = self.claude_cli_config.get_latest_path(self.asset_type)

        try:
            self.file_io.write_text(latest_path, video_player_content)
            self.logger.info(f" VideoPlayer file saved to Claude CLI location: {latest_path}")

            # Now process and save to versioned output and update manifest
            version, file_path = self.process_output()

            if not version or not file_path:
                self.logger.error("Failed to process and version the VideoPlayer output")
                return False, None

            self.logger.info(f" VideoPlayer processed and saved as {version}: {file_path}")
            return True, file_path
        except Exception as e:
            self.logger.error(f"Failed to save and process VideoPlayer file: {str(e)}")
            return False, None

    def validate_output(self) -> bool:
        self.logger.info("Validating video output...")

        total_scenes = self.metadata_controller.get_total_scenes(self.asset_type)
        if total_scenes == 0:
            self.logger.error("No scenes found in metadata (total_scenes is 0)")
            return False

        self.gen_metadata_controller.set_metadata({"total_scenes": total_scenes})
        self.logger.info(f"Expecting {total_scenes} scenes (0 to {total_scenes - 1})")

        # Get the latest folder path from the template
        latest_path_template = self.claude_cli_scene_output_path
        latest_folder = Path(latest_path_template).parent

        # Check each scene file
        missing_scenes = []
        existing_scenes = []

        for scene_index in range(total_scenes):
            scene_file_path = latest_folder / f"scene_{scene_index}.tsx"
            if scene_file_path.exists():
                existing_scenes.append(scene_index)
            else:
                missing_scenes.append(scene_index)

        # Log results
        self.logger.info(f"Found {len(existing_scenes)}/{total_scenes} scene files")

        if missing_scenes:
            missing_scenes_str = ', '.join(str(s) for s in missing_scenes)
            sys.stderr.write(f"Missing scenes: [{missing_scenes_str}]\n")
            sys.stderr.write(f"Regenerate these scenes: {missing_scenes_str}\n")
            return False

        self.logger.info("All scene files are present")
        return True


    def process(self) -> Tuple[bool, Optional[str]]:
        if not self.validate_output():
            sys.exit(1)

        success, file_path = self.generate_and_save_from_direction()
        if not success or not file_path:
            self.logger.error("Failed to generate and save VideoPlayer from direction file")
            return False, None
        return True, file_path

    def run(self) -> Tuple[bool, Optional[str]]:
        self.gen_metadata_controller.set_metadata({"type":"claude_cli"})
        result = self.process()
        try:
            deployedData=self.deployService.run()
            if not deployedData['success']:
                self.logger.info("Failed to deploy video")
            else:
                self.gen_metadata_controller.set_metadata({"video_url": deployedData['url']})
                self.force_logging(f"Video deployed successfully")
                self.force_logging(f"Video URL: {deployedData['url']}")
        except Exception as e:
            self.logger.error(f"Failed to deploy video: {str(e)}")
        self.gen_metadata_controller.save_metadata()
        return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post-process React video component")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--log', action='store_true', default=True, help='Enable console logging (default: True)')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')
    args = parser.parse_args()

    # Set console logging based on argument
    set_console_logging(args.log)

    post_processor = VideoContentPostProcessing(topic=args.topic)

    # Generate VideoPlayer with scene imports (instead of merging scene code)
    success, file_path = post_processor.run()
    if success and file_path:
        post_processor.logger.info(f" Successfully generated VideoPlayer")
        post_processor.logger.info(f" Output file: {file_path}")
    else:
        post_processor.logger.error(" Failed to generate VideoPlayer")
        sys.exit(1)

    post_processor.logger.info(" React video post-processing completed successfully")

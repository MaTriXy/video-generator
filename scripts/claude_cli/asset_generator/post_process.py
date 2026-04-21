"""
Asset Generator Post-Process - Discovers asset files and mirrors them into the topic's public/ folder.
"""

import re
import shutil
import sys
import os
import json
import csv
import asyncio
from typing import Optional, Tuple, List, Dict
from pathlib import Path
from glob import glob

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.enums import AssetType
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController
from scripts.logging_config import set_console_logging


class AssetGeneratorPostProcess(BasePostProcess):

    def __init__(self, topic: str):
        super().__init__(
            logger_name='AssetGeneratorPostProcess',
            log_file_name='asset-generator-post-process',
            topic=topic,
            asset_type=AssetType.ASSETS,
        )
        self.metadata_controller = VideoStepMetadataController(topic)
        self.asset_type_map = self._build_asset_type_map()

    def _build_asset_type_map(self) -> Dict[str, str]:
        """Build map of asset name -> asset-type from the Direction output's required_assets."""
        direction_manifest = self.manifest_controller.get_field(AssetType.DIRECTION)
        direction_path = direction_manifest.get('path') if direction_manifest else None
        if not direction_path:
            self.logger.warning("No Direction path found in manifest, asset type map will be empty")
            return {}
        direction = self.file_io.read_json(direction_path)
        if not direction:
            self.logger.warning("Failed to read Direction file, asset type map will be empty")
            return {}
        required_assets = direction.get('required_assets', [])
        return {asset.get('name', ''): asset.get('asset-type', '') for asset in required_assets}

    def _get_uploaded_assets_from_direction(self) -> List[Dict]:
        """Get assets marked as 'uploaded' in the Direction output's required_assets."""
        direction_manifest = self.manifest_controller.get_field(AssetType.DIRECTION)
        direction_path = direction_manifest.get('path') if direction_manifest else None
        if not direction_path:
            return []
        direction = self.file_io.read_json(direction_path)
        if not direction:
            return []
        required_assets = direction.get('required_assets', [])
        return [a for a in required_assets if a.get('asset-type') == 'uploaded']

    @try_catch
    def extract_svgs_from_file(self, file_path: Path) -> List[Dict[str, str]]:
        content = file_path.read_text(encoding='utf-8')
        pattern = r'<!--\s*ASSET:\s*(\S+)\s*-->\s*((?:<!--\s*COMPOSITION:[^>]+-->\s*)?<svg[\s\S]*?</svg>)'
        matches = re.findall(pattern, content, re.IGNORECASE)

        assets = []
        for asset_name, svg_content in matches:
            assets.append({'name': asset_name.strip(), 'content': svg_content.strip()})

        self.logger.info(f"Extracted {len(assets)} assets from file")
        return assets

    @try_catch
    def load_fetched_assets_list(self, latest_dir: Path) -> List[Dict[str, str]]:
        """Load the pre-built list of fetched asset file paths written by DirectAssetHandler."""
        fetched_list_path = latest_dir / "fetched_assets.json"
        if not fetched_list_path.exists():
            return []
        fetched_list = self.file_io.read_json(str(fetched_list_path))
        if not fetched_list:
            return []
        assets = []
        for item in fetched_list:
            file_path = Path(item.get("file_path", ""))
            if not file_path.exists():
                self.logger.warning(f"Fetched asset file not found: {file_path}")
                continue
            content = file_path.read_text(encoding='utf-8') if file_path.suffix == '.svg' else ""
            assets.append({'name': item.get("name", file_path.stem), 'content': content, 'file_path': file_path})
        self.logger.info(f"Loaded {len(assets)} fetched assets from list")
        return assets

    @try_catch
    def discover_asset_files(self, latest_dir: Path) -> List[Dict[str, str]]:
        """Discover individual asset files saved directly into latest_dir (legacy fallback).
        Deduplicates by asset name (stem), preferring png > jpg/jpeg/webp > svg."""
        extension_priority = {'.png': 0, '.jpg': 1, '.jpeg': 1, '.webp': 2, '.svg': 3}
        asset_files = [f for f in latest_dir.iterdir() if f.is_file() and f.suffix in extension_priority and f.stem != 'latest_assets']

        # Deduplicate: keep highest-priority (lowest number) extension per stem
        best_per_name: Dict[str, Path] = {}
        for asset_file in asset_files:
            name = asset_file.stem
            if name not in best_per_name or extension_priority[asset_file.suffix] < extension_priority[best_per_name[name].suffix]:
                best_per_name[name] = asset_file

        assets = []
        for asset_file in best_per_name.values():
            content = asset_file.read_text(encoding='utf-8') if asset_file.suffix == '.svg' else ""
            assets.append({'name': asset_file.stem, 'content': content, 'file_path': asset_file})
        self.logger.info(f"Discovered {len(assets)} asset files in {latest_dir}")
        return assets

    def _load_asset_descriptions(self, latest_dir: Path) -> Dict[str, Dict]:
        """Load asset descriptions from asset_description.json written by the asset fetcher.
        Format: {name: {description: str, asset_type: str}}"""
        desc_path = latest_dir / "asset_description.json"
        if not desc_path.exists():
            self.logger.warning("asset_description.json not found, descriptions will be empty")
            return {}
        descriptions = self.file_io.read_json(str(desc_path))
        if not descriptions or not isinstance(descriptions, dict):
            self.logger.warning("asset_description.json is empty or invalid")
            return {}
        self.logger.info(f"Loaded {len(descriptions)} asset descriptions")
        return descriptions

    def _mirror_assets_to_public(self, assets: List[Dict], asset_descriptions: Dict[str, Dict]) -> List[Dict]:
        """Copy asset files into the topic's public/ folder so Remotion Studio's
        staticFile() can serve them. Returns asset entries with the filename as `url`."""
        public_dir = Path(project_root) / "Outputs" / self.claude_cli_config.topic / "public"
        public_dir.mkdir(parents=True, exist_ok=True)

        saved_assets = []
        for asset in assets:
            asset_name = asset['name']
            file_path_obj = asset.get('file_path')
            if not file_path_obj or not file_path_obj.exists():
                self.logger.error(f"Asset file not found: {asset_name}")
                continue

            try:
                dest = public_dir / file_path_obj.name
                shutil.copyfile(file_path_obj, dest)
                asset_desc_entry = asset_descriptions.get(asset_name, {})
                composition = asset_desc_entry.get("description", "") if isinstance(asset_desc_entry, dict) else asset_desc_entry
                asset_type = asset_desc_entry.get("asset_type", "") if isinstance(asset_desc_entry, dict) else self.asset_type_map.get(asset_name, "")
                aspect_ratio = asset_desc_entry.get("aspect_ratio", "1:1") if isinstance(asset_desc_entry, dict) else "1:1"
                saved_assets.append({
                    "name": asset_name,
                    "asset_type": asset_type,
                    "url": file_path_obj.name,
                    "composition": composition,
                    "aspect_ratio": aspect_ratio,
                })
                self.logger.info(f"Mirrored asset to public/: {asset_name} -> {dest}")
            except Exception as e:
                self.logger.error(f"Failed to copy asset '{asset_name}' to public/: {e}")

        return saved_assets

    def _detect_agent_created_assets(self, logs_dir: Path) -> set:
        """Parse subagent logs to find assets the agent created from scratch via Write tool."""
        agent_created = set()
        log_pattern = str(logs_dir / "subagent_*.json")
        log_files = glob(log_pattern)
        if not log_files:
            self.logger.info("No subagent log files found for agent-created detection")
            return agent_created

        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to read subagent log {log_file}: {e}")
                continue

            for entry in entries:
                if entry.get("type") != "assistant":
                    continue
                message = entry.get("message", {})
                content_blocks = message.get("content", [])
                for block in content_blocks:
                    if not isinstance(block, dict):
                        continue
                    tool_name = block.get("name", "")
                    if block.get("type") == "tool_use" and tool_name == "Write":
                        file_path = block.get("input", {}).get("file_path", "")
                        if file_path:
                            stem = Path(file_path).stem
                            agent_created.add(stem)
                            self.logger.info(f"Detected agent-created asset: {stem} (from {tool_name} tool in logs)")

        return agent_created

    def _enrich_analytics_with_source(self, latest_dir: Path, agent_created_assets: set):
        """Update asset_analytics.json with source field (tool_fetched vs agent_created)."""
        analytics_path = latest_dir / "asset_analytics.json"
        if not analytics_path.exists():
            self.logger.info("No asset_analytics.json found, skipping source enrichment")
            return

        try:
            with open(analytics_path, "r", encoding="utf-8") as f:
                analytics = json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to read asset_analytics.json: {e}")
            return

        for entry in analytics:
            asset_name = entry.get("asset_name", "")
            entry["num_attempts"] = len(entry.get("attempts", []))
            entry["total_elapsed_ms"] = sum(a.get("elapsed_ms", 0) for a in entry.get("attempts", []))
            if asset_name in agent_created_assets:
                entry["source"] = "agent_created"
            else:
                entry["source"] = "tool_fetched"

        try:
            with open(analytics_path, "w", encoding="utf-8") as f:
                json.dump(analytics, f, indent=2)
            self.logger.info(f"Enriched {len(analytics)} analytics entries with source info")
        except Exception as e:
            self.logger.warning(f"Failed to write enriched asset_analytics.json: {e}")

    def _generate_analytics_csv(self, latest_dir: Path):
        """Convert asset_analytics.json to a CSV with per-attempt columns (e.g. provider_A1, search_keywords_A2)."""
        analytics_path = latest_dir / "asset_analytics.json"
        if not analytics_path.exists():
            self.logger.info("No asset_analytics.json found, skipping CSV generation")
            return

        try:
            with open(analytics_path, "r", encoding="utf-8") as f:
                analytics = json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to read asset_analytics.json for CSV: {e}")
            return

        # Determine max attempts across all assets
        max_attempts = max((len(entry.get("attempts", [])) for entry in analytics), default=0)

        # Build column list
        base_columns = ["asset_id", "asset_name", "asset_type", "num_attempts", "total_elapsed_ms", "final_status", "output_path", "file_format", "message", "source"]
        attempt_fields = ["provider", "search_keywords", "candidates_found", "top_n", "selected_candidate",
                          "match_type", "match_score", "suggested_keywords", "elapsed_ms", "status"]
        attempt_columns = [f"{field}_A{i}" for i in range(1, max_attempts + 1) for field in attempt_fields]
        columns = base_columns + attempt_columns

        csv_path = latest_dir / "asset_analytics.csv"
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for entry in analytics:
                    row = {col: entry.get(col, "") for col in base_columns}
                    for attempt in entry.get("attempts", []):
                        n = attempt.get("attempt_number", 1)
                        suffix = f"_A{n}"
                        for field in attempt_fields:
                            val = attempt.get(field, "")
                            if isinstance(val, list):
                                val = " | ".join(str(v) for v in val)
                            row[field + suffix] = val if val is not None else ""
                    writer.writerow(row)
            self.logger.info(f"Generated analytics CSV at {csv_path}")
        except Exception as e:
            self.logger.warning(f"Failed to write asset_analytics.csv: {e}")

    @try_catch(return_on_error=(False, "Assets post-processing failed due to an unexpected error"))
    async def process(self) -> Tuple[bool, Optional[str]]:
        self.logger.info("Processing asset generator output")

        # Check if direction had any required assets
        has_required_assets = len(self.asset_type_map) > 0

        if not has_required_assets:
            self.logger.info("No required assets from direction — completing with empty asset list")
            self.gen_metadata_controller.set_metadata({"total_assets": 0})
            empty_output = {"assets": []}
            latest_path = Path(self.claude_cli_config.get_latest_path(self.asset_type))
            latest_dir = latest_path.parent
            latest_dir.mkdir(parents=True, exist_ok=True)
            latest_json = latest_dir / "latest_assets.json"
            self.file_io.write_json(str(latest_json), empty_output)
            file_path, version = self.output_controller.save_output(self.asset_type, str(latest_json))
            if file_path:
                self.file_io.write_json(file_path, empty_output)
                self.manifest_controller.update_file(self.asset_type, file_path, version)
            return True, file_path

        latest_path = Path(self.claude_cli_config.get_latest_path(self.asset_type))
        latest_dir = latest_path.parent
        latest_dir.mkdir(parents=True, exist_ok=True)

        # Use the fetched assets list from DirectAssetHandler if available,
        # fall back to file discovery, then to extracting from combined file
        assets = self.load_fetched_assets_list(latest_dir)
        if not assets:
            assets = self.discover_asset_files(latest_dir)
        if not assets and latest_path.exists():
            assets = self.extract_svgs_from_file(latest_path)

        self.gen_metadata_controller.set_metadata({"total_assets": len(assets)})

        # Get version first (needed for logs lookup)
        version = self.manifest_controller.get_current_gen_version(self.asset_type)

        saved_assets = []

        if assets:
            # Detect agent-created assets from subagent logs in the versioned directory (e.g. Assets/v2/logs/)
            versioned_dir = latest_dir.parent / f"v{version}"
            logs_dir = versioned_dir / "logs"
            agent_created_assets = self._detect_agent_created_assets(logs_dir)
            self._enrich_analytics_with_source(latest_dir, agent_created_assets)
            self._generate_analytics_csv(latest_dir)

            # Load asset descriptions written by the asset fetcher
            asset_descriptions = self._load_asset_descriptions(latest_dir)

            # Mirror assets into the topic's public/ folder for Remotion Studio
            saved_assets = self._mirror_assets_to_public(assets, asset_descriptions)
        else:
            self.logger.info("No fetched assets to process - direction returned empty asset list")

        # Append uploaded assets from Direction's required_assets (asset-type: "uploaded")
        uploaded_direction_assets = self._get_uploaded_assets_from_direction()
        if uploaded_direction_assets:
            for ua in uploaded_direction_assets:
                saved_assets.append({
                    "name": ua.get("name", ""),
                    "asset_type": "uploaded",
                    "url": ua.get("url", ""),
                    "description": ua.get("description", ""),
                })
            self.logger.info(f"Appended {len(uploaded_direction_assets)} uploaded assets from direction")
        else:
            # Fallback: append uploaded assets from manifest metadata
            course_metadata = self.manifest_controller.get_metadata()
            uploaded_assets = course_metadata.get("uploaded_assets", [])
            for ua in uploaded_assets:
                saved_assets.append({
                    "name": ua.get("name", ""),
                    "url": ua.get("url", ""),
                    "description": ua.get("description", ""),
                })
            self.logger.info(f"Appended {len(uploaded_assets)} uploaded assets from manifest metadata")

        if not saved_assets:
            error_msg = "No assets found - neither fetched assets nor uploaded assets available"
            self.logger.error(error_msg)
            return False, error_msg

        latest_json = latest_dir / "latest_assets.json"
        self.file_io.write_json(str(latest_json), {"assets": saved_assets})

        file_path, version = self.output_controller.save_output(self.asset_type, str(latest_json))
        if not file_path:
            error_msg = "Failed to save versioned output for assets"
            self.logger.error(error_msg)
            return False, error_msg

        self.file_io.write_json(file_path, {"assets": saved_assets})
        self.manifest_controller.update_file(self.asset_type, file_path, version)

        self.logger.info("Asset generator output processed successfully")
        return True, file_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post-process asset generator")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for asset generation')
    parser.add_argument('--log', action='store_true', default=True, help='Enable console logging (default: True)')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')
    args = parser.parse_args()

    set_console_logging(args.log)

    post_processor = AssetGeneratorPostProcess(topic=args.topic)

    success, file_path = asyncio.run(post_processor.run())

    if success and file_path:
        post_processor.logger.info("Successfully processed asset generator output")
        post_processor.logger.info(f"Output file: {file_path}")
    else:
        post_processor.logger.error("Failed to process asset generator output")
        sys.exit(1)

    post_processor.logger.info("Asset generator post-processing completed successfully")

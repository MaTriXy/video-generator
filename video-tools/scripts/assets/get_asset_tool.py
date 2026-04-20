"""Batch asset fetcher. Extracted from the deleted MCP controller."""
import asyncio
import json
import os
import time

from scripts.logging_config import get_utility_logger
from scripts.assets.emoji.emoji_asset_provider import EmojiAssetProvider
from scripts.assets.company_logos.company_logos_asset_provider import CompanyLogosAssetProvider

logger = get_utility_logger('tools.get_asset_tool')

_description_locks: dict[str, asyncio.Semaphore] = {}
_analytics_locks: dict[str, asyncio.Semaphore] = {}


def _get_description_lock(output_path: str) -> asyncio.Semaphore:
    if output_path not in _description_locks:
        _description_locks[output_path] = asyncio.Semaphore(1)
    return _description_locks[output_path]


def _get_analytics_lock(output_path: str) -> asyncio.Semaphore:
    if output_path not in _analytics_locks:
        _analytics_locks[output_path] = asyncio.Semaphore(1)
    return _analytics_locks[output_path]


async def _save_asset_descriptions(output_path: str, results: list[dict]):
    new_descs = {
        r["name"]: {
            "description": r["description"],
            "asset_type": r.get("asset_type", "emoji"),
            "aspect_ratio": r["aspect_ratio"],
        }
        for r in results if r.get("description")
    }
    if not new_descs:
        return

    async with _get_description_lock(output_path):
        desc_path = os.path.join(output_path, "asset_description.json")
        existing = {}
        if os.path.isfile(desc_path):
            with open(desc_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.update(new_descs)
        os.makedirs(output_path, exist_ok=True)
        with open(desc_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        logger.info(f"[GET_ASSET] Saved {len(new_descs)} descriptions to {desc_path}")


async def _save_asset_analytics(output_path: str, analytics_entries: list[dict]):
    if not analytics_entries:
        return

    async with _get_analytics_lock(output_path):
        analytics_path = os.path.join(output_path, "asset_analytics.json")
        existing = []
        if os.path.isfile(analytics_path):
            with open(analytics_path, "r", encoding="utf-8") as f:
                existing = json.load(f)

        id_to_entry = {entry.get("asset_id"): entry for entry in existing if entry.get("asset_id")}

        for new_entry in analytics_entries:
            aid = new_entry.get("asset_id")
            if aid and aid in id_to_entry:
                existing_attempts = id_to_entry[aid]["attempts"]
                new_attempt = new_entry["attempts"][0]
                new_attempt["attempt_number"] = len(existing_attempts) + 1
                existing_attempts.append(new_attempt)
                id_to_entry[aid]["final_status"] = new_entry["final_status"]
                id_to_entry[aid]["output_path"] = new_entry["output_path"]
                id_to_entry[aid]["message"] = new_entry["message"]
            else:
                existing.append(new_entry)
                if aid:
                    id_to_entry[aid] = new_entry

        os.makedirs(output_path, exist_ok=True)
        with open(analytics_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        logger.info(f"[GET_ASSET] Saved {len(analytics_entries)} analytics entries to {analytics_path}")


async def get_asset_batch(
    assets: list[dict],
    art_style: str = "",
    output_path: str = "",
    max_candidates: int = 10,
) -> list[dict]:
    """Fetch a batch of assets in parallel.

    assets: list of {"name": str, "description": str, "asset_type"?: str,
                     "keywords"?: list[str], "asset_id"?: str}
    """
    if len(assets) > 10:
        return [{
            "svg_code": None, "output_path": None, "name": None,
            "message": "Maximum 10 assets per request.",
        }]

    start_time = time.time()
    logger.info(f"[GET_ASSET] Request: {len(assets)} assets, art_style='{art_style}', output_path='{output_path}'")

    async def _fetch_one(asset: dict) -> tuple[dict, dict]:
        raw_name = asset["name"]
        name = raw_name.split(",")[0].split(";")[0].strip().replace(" ", "_")
        description = asset["description"]
        asset_type = asset.get("asset_type", "emoji")
        keywords = asset.get("keywords", [])
        asset_id = asset.get("asset_id", "")
        file_name = asset_id if asset_id else name
        asset_output = os.path.join(output_path, file_name) if output_path else ""
        t0 = time.time()

        if asset_type == "company-logo":
            provider = CompanyLogosAssetProvider()
            result = await provider.get_asset(name, description, art_style, asset_output, max_candidates)
        else:
            # All other asset types (emoji, illustration, human-character, default)
            # resolve via the iconify icon index.
            provider = EmojiAssetProvider()
            result = await provider.get_asset(name, description, art_style, asset_output, max_candidates)

        elapsed = (time.time() - t0) * 1000
        has_asset = result.get("svg_code") or result.get("asset_link")
        status = "OK" if has_asset else "MISSING"
        logger.info(f"[GET_ASSET] {file_name} ({asset_type}): {result['message']} in {elapsed:.2f}ms [{status}]")
        result["name"] = file_name
        result["elapsed_ms"] = round(elapsed, 2)

        provider_analytics = provider.get_analytics()
        analytics_entry = {
            "asset_id": asset_id,
            "asset_name": file_name,
            "asset_type": asset_type,
            "attempts": [{
                "attempt_number": 1,
                "provider": (
                    "logo_dev+icon_libraries" if asset_type == "company-logo"
                    else "icon_index"
                ),
                "search_keywords": keywords,
                "candidates_found": provider_analytics.get("candidates_found", 0),
                "top_n": provider_analytics.get("top_n", []),
                "selected_candidate": provider_analytics.get("selected_candidate"),
                "match_type": provider_analytics.get("match_type", "not_found"),
                "match_score": provider_analytics.get("match_score"),
                "suggested_keywords": provider_analytics.get("suggested_keywords"),
                "short_agent_responses": provider_analytics.get("short_agent_responses", []),
                "elapsed_ms": round(elapsed, 2),
                "status": "found" if has_asset else "not_found",
            }],
            "final_status": "found" if has_asset else "not_found",
            "output_path": result.get("output_path"),
            "file_format": result.get("file_format"),
            "message": result.get("message", ""),
        }
        return result, analytics_entry

    fetch_results = await asyncio.gather(*[_fetch_one(a) for a in assets])
    results = [r[0] for r in fetch_results]
    analytics_entries = [r[1] for r in fetch_results]

    if output_path:
        await _save_asset_descriptions(output_path, results)
        await _save_asset_analytics(output_path, analytics_entries)

    total_elapsed = (time.time() - start_time) * 1000
    found = sum(1 for r in results if r.get("svg_code") or r.get("asset_link"))
    logger.info(f"[GET_ASSET] Complete: {found}/{len(assets)} found in {total_elapsed:.2f}ms")
    return results

"""
Base asset provider - Abstract interface for asset providers.
"""

import re
from abc import ABC, abstractmethod
from math import gcd
from pathlib import Path
from PIL import Image
from scripts.logging_config import get_utility_logger
from scripts.utility.short_agent import ShortAgent
from scripts.utility.prompt_loader import get_mcp_prompt


class BaseAssetProvider(ABC):
    """Base class for asset providers that search and rank assets."""

    def __init__(self, log_prefix: str):
        self.log_prefix = log_prefix
        self.logger = get_utility_logger(f'assets.{log_prefix.lower()}')
        self._analytics: dict = {}

    @property
    @abstractmethod
    def asset_type(self) -> str:
        """Return the asset type identifier, e.g. 'emoji' or 'illustration'."""

    @property
    @abstractmethod
    def file_format(self) -> str:
        """Return the file format, e.g. 'svg' or 'png'."""

    @abstractmethod
    async def search_candidates(self, keywords: str, art_style: str, max_candidates: int) -> list[str]:
        """Search for candidate asset names."""

    @abstractmethod
    def get_asset_content(self, asset_name: str) -> str | None:
        """Get the asset content (e.g. SVG code or thumbnail URL). Returns content string or None."""

    @abstractmethod
    async def _pick_best_visual(self, content_map: dict[str, str], description: str, name: str) -> tuple[str | None, str]:
        """
        Visual pick step: given a map of {candidate_name: content}, use LLM to pick the best match.
        Subclasses implement this with SVG text or base64 image analysis.

        Returns:
            (best name or None, description of what the chosen asset visually depicts)
        """

    def _compute_aspect_ratio(self, content: str, saved_path: str | None = None) -> str:
        """Compute aspect ratio. For SVGs parses attributes/viewBox, for images reads the file."""
        w_match = re.search(r'\bwidth=["\'](\d+(?:\.\d+)?)', content)
        h_match = re.search(r'\bheight=["\'](\d+(?:\.\d+)?)', content)
        if w_match and h_match:
            w, h = int(float(w_match.group(1))), int(float(h_match.group(1)))
            d = gcd(w, h)
            return f"{w // d}:{h // d}"

        vb = re.search(r'viewBox=["\'][\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)', content)
        if vb:
            w, h = int(float(vb.group(1))), int(float(vb.group(2)))
            d = gcd(w, h)
            return f"{w // d}:{h // d}"

        if saved_path and Path(saved_path).is_file():
            with Image.open(saved_path) as img:
                w, h = img.size
                d = gcd(w, h)
                return f"{w // d}:{h // d}"

        return "1:1"

    def reset_analytics(self):
        """Reset analytics for a new asset fetch."""
        self._analytics = {
            "candidates_found": 0,
            "top_n": [],
            "selected_candidate": None,
            "match_type": "not_found",
            "match_score": None,
            "suggested_keywords": None,
            "short_agent_responses": [],
        }

    def get_analytics(self) -> dict:
        """Return collected analytics data."""
        return self._analytics.copy()

    def _null_result(self, message: str) -> dict:
        self.logger.info(f"[{self.log_prefix}] {message}")
        return {
            "asset_link": None,
            "svg_code": None,
            "description": None,
            "output_path": None,
            "message": message,
            "asset_type": self.asset_type,
            "file_format": None,
            "aspect_ratio": "1:1",
        }

    def _parse_pick_response(self, raw: str, candidates: list[str]) -> tuple[str | None, str]:
        """Parse NAME/DESCRIPTION response from the pick-best agent."""
        name_match = re.search(r'NAME:\s*(.+)', raw, re.IGNORECASE)
        desc_match = re.search(r'DESCRIPTION:\s*(.+)', raw, re.IGNORECASE)

        chosen = name_match.group(1).strip() if name_match else "null"
        asset_description = desc_match.group(1).strip() if desc_match else ""

        if chosen == "null" or chosen.lower() == "none":
            self.logger.info(f"[{self.log_prefix}] Agent rejected all candidates")
            return None, ""

        matched = None
        if chosen in candidates:
            matched = chosen
        else:
            for n in candidates:
                if n in chosen:
                    matched = n
                    break

        if not matched:
            self.logger.warning(f"[{self.log_prefix}] Agent returned '{chosen}' not in candidates")
            return None, ""

        self.logger.info(f"[{self.log_prefix}] Selected: '{matched}' — {asset_description}")
        return matched, asset_description

    async def rank_top_n(self, candidates: list[str], name: str, description: str, top_n: int = 5) -> list[str]:
        """Agent call #1: rank candidates by name and return the top N matches."""
        if len(candidates) <= top_n:
            self._analytics["top_n"] = candidates
            return candidates
        self.logger.info(f"[{self.log_prefix}] Ranking----- {len(candidates)} candidates for name='{name}', picking top {top_n}")

        candidates_str = "\n".join(f"- {c}" for c in candidates)
        prompt = (
            f"Given these icon names (listed in priority order, earlier = higher priority):\n{candidates_str}\n\n"
            f"Pick the top {top_n} icon names that best match the description: {description} and name: {name}. "
            f"Prefer icons listed earlier (higher priority) when matches are equally good. but description matching is a prioirty"
            f"Return ONLY the exact icon names from the list, one per line, nothing else."
        )

        agent = ShortAgent(
            name="rank_top_n",
            system_prompt=get_mcp_prompt("rank_top_n", top_n=top_n),
        )
        result = await agent.ask(prompt, name)

        self._analytics["short_agent_responses"].append({
            "agent": "rank_top_n",
            "response": result.strip(),
        })

        picked = []
        for line in result.strip().splitlines():
            cleaned = line.strip().lstrip("- ").strip()
            if cleaned in candidates and cleaned not in picked:
                picked.append(cleaned)

        if not picked:
            self.logger.warning(f"[{self.log_prefix}] Agent returned no valid names, using first {top_n}")
            picked = candidates[:top_n]

        self._analytics["top_n"] = picked[:top_n]
        self.logger.info(f"[{self.log_prefix}] Top {top_n} by name: {picked}")
        return picked[:top_n]

    async def suggest_keywords(self, keywords: str, description: str) -> list[str]:
        """Use LLM to suggest alternative search keywords."""
        self.logger.info(f"[{self.log_prefix}] Suggesting keywords for: '{keywords}' — '{description}'")

        agent = ShortAgent(
            name="suggest_keywords",
            system_prompt=get_mcp_prompt("suggest_keywords"),
        )
        prompt = (
            f"Name : {keywords}\n"
            f"Description of the asset needed: {description}\n\n"
            f"The name returned no results from iconify library. "
            f"Suggest 3-5 comma-separated single-word keywords that would match. "
            f"Think of generic, universal icon names (e.g. 'rocket', 'gear', 'star', 'chart'). "
            f"Return ONLY the comma-separated words, nothing else."
        )

        result = await agent.ask(prompt, keywords)
        suggested = [kw.strip() for kw in result.split(",") if kw.strip()]
        self._analytics["short_agent_responses"].append({
            "agent": "suggest_keywords",
            "response": result.strip(),
        })
        self._analytics["suggested_keywords"] = suggested
        self.logger.info(f"[{self.log_prefix}] Suggested keywords: {suggested}")
        return suggested

    async def _search_and_pick(self, keywords: str, name: str, description: str, art_style: str, max_candidates: int, top_n: int = 3) -> tuple[str | None, str]:
        """
        Core flow: search → rank top N by name → fetch content → agent picks visually.

        Returns:
            (best name or None, asset description)
        """
        candidates = await self.search_candidates(keywords, art_style, max_candidates)
        self._analytics["candidates_found"] = len(candidates)
        if not candidates:
            return None, ""

        top = await self.rank_top_n(candidates, name, description, top_n)

        content_map = {}
        for candidate_name in top:
            content = self.get_asset_content(candidate_name)
            if content:
                content_map[candidate_name] = content

        if not content_map:
            return None, ""

        return await self._pick_best_visual(content_map, description, name)

    async def find_best(self, name: str, description: str, art_style: str, max_candidates: int) -> tuple[str | None, str, str]:
        """
        Search → rank top N → pick visually → if null, suggest keywords and retry once.

        Returns:
            (best_name, message, asset_description)
        """
        best, asset_desc = await self._search_and_pick(name, name, description, art_style, max_candidates)
        if best:
            self._analytics["selected_candidate"] = best
            self._analytics["match_type"] = "direct"
            return best, f"Direct match: '{best}'", asset_desc

        self.logger.info(f"[{self.log_prefix}] No match for '{name}', requesting LLM keyword suggestions")
        suggested = await self.suggest_keywords(name, description)
        if not suggested:
            self._analytics["match_type"] = "not_found"
            return None, f"No matching asset found for '{name}'", ""

        self.logger.info(f"[{self.log_prefix}] Retrying with suggested keywords: {suggested}")
        best, asset_desc = await self._search_and_pick(",".join(suggested), name, description, art_style, max_candidates)
        if best:
            self._analytics["selected_candidate"] = best
            self._analytics["match_type"] = "suggested_keywords"
            return best, f"No direct match for '{name}', found '{best}' via suggested keywords: {suggested}", asset_desc

        self._analytics["match_type"] = "not_found"
        return None, f"No matching asset found for '{name}'", ""

    async def save_asset(self, content: str, output_path: str, asset_description: str = "") -> str | None:
        """Save asset content to disk. Override in subclass for non-text assets (e.g. download from URL)."""
        save_path = str(Path(output_path).with_suffix(".svg"))
        save_file = Path(save_path)
        save_file.parent.mkdir(parents=True, exist_ok=True)
        if asset_description:
            content = f"<!-- COMPOSITION: {asset_description} -->\n{content}"
        save_file.write_text(content, encoding="utf-8")
        return save_path

    async def get_asset(self, keywords: str, description: str, art_style: str, output_path: str, max_candidates: int) -> dict:
        """Full pipeline: find_best → save → return result dict."""
        self.reset_analytics()
        best, message, asset_desc = await self.find_best(keywords, description, art_style, max_candidates)
        if not best:
            return self._null_result(message)

        content = self.get_asset_content(best)
        if not content:
            return self._null_result(f"Found '{best}' but failed to get content")

        saved_path = await self.save_asset(content, output_path, asset_desc) if output_path else None

        return {
            "asset_link": saved_path,
            "svg_code": content if self.file_format == "svg" else None,
            "description": asset_desc or None,
            "output_path": saved_path,
            "message": message,
            "asset_type": self.asset_type,
            "file_format": self.file_format,
            "aspect_ratio": self._compute_aspect_ratio(content, saved_path),
        }

"""
Emoji asset provider - Searches local icon indexes and ranks candidates with LLM.
"""

from scripts.assets.base_asset_provider import BaseAssetProvider
from scripts.assets.emoji.icon_search_engine import search_icons, get_icon_svg
from scripts.utility.short_agent import ShortAgent
from scripts.utility.prompt_loader import get_mcp_prompt


class EmojiAssetProvider(BaseAssetProvider):

    def __init__(self):
        super().__init__(log_prefix="ICON_ASSET")

    @property
    def asset_type(self) -> str:
        return "emoji"

    @property
    def file_format(self) -> str:
        return "svg"

    async def search_candidates(self, keywords: str, art_style: str, max_candidates: int) -> list[str]:
        keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        if not keyword_list:
            return []

        per_keyword = max(1, max_candidates // len(keyword_list))
        high = {}
        medium = {}
        for kw in keyword_list:
            results = search_icons(name_query=kw, max_results=per_keyword, video_style=art_style)
            for icon_name in results.get("highPriority", []):
                if icon_name not in high and icon_name not in medium:
                    high[icon_name] = True
            for icon_name in results.get("mediumPriority", []):
                if icon_name not in high and icon_name not in medium:
                    medium[icon_name] = True

        # High priority first, then medium
        return (list(high.keys()) + list(medium.keys()))[:max_candidates]

    def get_asset_content(self, icon_name: str) -> str | None:
        svg = get_icon_svg(icon_name, color='#000')
        if not svg:
            self.logger.warning(f"[{self.log_prefix}] No SVG found for '{icon_name}'")
            return None

        # Add xlink namespace if SVG uses xlink:href but doesn't declare it
        if "xlink:" in svg and 'xmlns:xlink' not in svg:
            svg = svg.replace('<svg ', '<svg xmlns:xlink="http://www.w3.org/1999/xlink" ', 1)

        return svg

    async def _pick_best_visual(self, content_map: dict[str, str], description: str, name: str) -> tuple[str | None, str]:
        """Send SVG code to agent, pick the best match for the description."""
        if not content_map:
            return None, ""

        names = list(content_map.keys())
        self.logger.info(f"[{self.log_prefix}] Picking best from {len(content_map)} SVGs for: '{description}'")

        entries = "\n\n".join(
            f"--- {n} ---\n{svg}" for n, svg in content_map.items()
        )
        prompt = (
            f"<input>\nDescription of the asset needed: {description}\n\n"
            f"Here are {len(content_map)} SVG icons:\n\n{entries}\n</input>\n\n"
            f"Pick the single icon name that best visually represents the description. "
            f"If NONE match, respond exactly: NAME: null DESCRIPTION: null\n"
            f"Otherwise respond in EXACTLY this format with NO other text:\n"
            f"NAME: <exact icon name>\n"
            f"DESCRIPTION: <brief description of what the chosen SVG visually depicts. Should have if its multicolor or monotone black color and the icon style, if its suitable for dark background or light background>"
        )

        agent = ShortAgent(
            name="pick_best_svg",
            system_prompt=get_mcp_prompt("pick_best_svg"),
        )
        raw = (await agent.ask(prompt, name)).strip()
        self._analytics["short_agent_responses"].append({
            "agent": "pick_best_svg",
            "response": raw,
        })
        return self._parse_pick_response(raw, names)

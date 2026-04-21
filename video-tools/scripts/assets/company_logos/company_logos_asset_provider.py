import os
import re
import httpx
from pathlib import Path

from scripts.assets.base_asset_provider import BaseAssetProvider
from scripts.assets.emoji.icon_search_engine import search_icons, get_icon_svg
from scripts.assets.video_style_config import COMPANY_LOGO_LIBRARIES
from scripts.utility.short_agent import ShortAgent
from scripts.utility.prompt_loader import get_mcp_prompt

LOGO_DEV_API_BASE = "https://api.logo.dev"


async def _download_to_file(url: str, output_path: str) -> bool:
    """Download a URL to a local file. Returns True on success."""
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
    return True


class CompanyLogosAssetProvider(BaseAssetProvider):

    def __init__(self):
        super().__init__(log_prefix="COMPANY_LOGOS")
        self._logo_dev_publishable_key = os.environ.get("LOGO_DEV_PUBLISHABLE_KEY", "")
        self._logo_dev_secret_key = os.environ.get("LOGO_DEV_SECRET_KEY", "")

    @property
    def asset_type(self) -> str:
        return "company-logos"

    @property
    def file_format(self) -> str:
        return ""

    async def _search_logo_dev(self, name: str) -> list[dict]:
        """Search Logo.dev Brand Search API for company domains. Returns list of {name, domain}."""
        if not self._logo_dev_secret_key:
            self.logger.warning(f"[{self.log_prefix}] LOGO_DEV_SECRET_KEY not set, skipping Logo.dev search")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{LOGO_DEV_API_BASE}/search",
                    params={"q": name, "strategy": "match"},
                    headers={"Authorization": f"Bearer {self._logo_dev_secret_key}"},
                )
                response.raise_for_status()
                results = response.json()

            self.logger.info(f"[{self.log_prefix}] Logo.dev search for '{name}': {len(results)} results")
            return results if isinstance(results, list) else []
        except Exception as e:
            self.logger.warning(f"[{self.log_prefix}] Logo.dev search failed for '{name}': {e}")
            return []

    async def _pick_logo_domain(self, results: list[dict], name: str, description: str) -> dict | None:
        """Use a ShortAgent to pick the correct company domain from Logo.dev search results."""
        candidates_str = "\n".join(
            f"- {r.get('name', '')} ({r.get('domain', '')})" for r in results
        )
        prompt = (
            f"Company to find: {name}\nDescription: {description}\n\n"
            f"Logo.dev search results:\n{candidates_str}\n\n"
            f"Pick the single result that best matches the company '{name}'.\n"
            f"Return ONLY the exact domain (e.g., apple.com), nothing else."
        )

        agent = ShortAgent(
            name="pick_logo_domain",
            system_prompt=get_mcp_prompt("pick_logo_domain"),
        )
        raw = await agent.ask(prompt, name)

        self._analytics["short_agent_responses"].append({
            "agent": "pick_logo_domain",
            "response": raw.strip(),
        })

        picked_domain = raw.strip().lower()
        for r in results:
            if r.get("domain", "").lower() == picked_domain:
                return r
        return None

    async def get_logo_icon(self, name: str, output_path: str, description: str) -> dict | None:
        """Fetch a company logo via Logo.dev. Returns result dict or None if not found."""
        if not self._logo_dev_secret_key:
            return None

        results = await self._search_logo_dev(name)
        if not results:
            return None

        chosen = await self._pick_logo_domain(results, name, description)
        if not chosen:
            return None

        domain = chosen.get("domain", "")
        logo_url = chosen.get("logo_url", "")
        if not logo_url:
            return None

        save_path = str(Path(output_path).with_suffix(".png")) if output_path else None

        if save_path:
            try:
                await _download_to_file(logo_url, save_path)
            except Exception as e:
                self.logger.warning(f"[{self.log_prefix}] Failed to download Logo.dev logo for '{domain}': {e}")
                return None

        self.logger.info(f"[{self.log_prefix}] Logo.dev: saved logo for '{domain}' to '{save_path}'")
        return self._build_result("", save_path, f"Found on Logo.dev: '{domain}'", description, file_format="png")

    async def get_asset(self, keywords: str, description: str, art_style: str, output_path: str, max_candidates: int) -> dict:
        self.reset_analytics()
        name = re.sub(r'[_\-\.\,\;\:\!\@\#\$\%\^\&\*\(\)\[\]\{\}\|\\\/\~\`\+\=]+', ' ', keywords).strip()
        name = re.sub(r'\s+', ' ', name)

        # Step 0: Search iconify company-logo libraries (simple-icons etc.)
        if COMPANY_LOGO_LIBRARIES:
            self.logger.info(f"[{self.log_prefix}] Step 0: Searching libraries {COMPANY_LOGO_LIBRARIES} for '{name}'")
            candidates = self._search_specific_libraries(name, max_candidates)
            self._analytics["candidates_found"] = len(candidates)
            if candidates:
                top = await self.rank_top_n(candidates, name, description, top_n=1)
                if top:
                    chosen = top[0]
                    svg = self._get_local_svg(chosen)
                    if svg:
                        self._analytics["selected_candidate"] = chosen
                        self._analytics["match_type"] = "direct"
                        saved = await self.save_asset(svg, output_path) if output_path else None
                        return self._build_result(svg, saved, f"Found in icon libraries: '{chosen}'", description)

        # Step 1: Try Logo.dev Brand Search API
        self.logger.info(f"[{self.log_prefix}] Step 1: Searching Logo.dev for '{name}'")
        logo_dev_result = await self.get_logo_icon(name, output_path, description)
        if logo_dev_result:
            self._analytics["selected_candidate"] = logo_dev_result.get("message", "")
            self._analytics["match_type"] = "logo_dev"
            return logo_dev_result

        self._analytics["match_type"] = "not_found"
        return self._null_result(f"No company logo found for '{name}'")

    def _get_local_svg(self, icon_name: str) -> str | None:
        svg = get_icon_svg(icon_name, color='#000')
        if not svg or svg.startswith("Error:"):
            return None
        if "xlink:" in svg and 'xmlns:xlink' not in svg:
            svg = svg.replace('<svg ', '<svg xmlns:xlink="http://www.w3.org/1999/xlink" ', 1)
        return svg

    def _build_result(self, content: str, saved_path: str | None, message: str, description: str, file_format: str = "svg") -> dict:
        return {
            "asset_link": saved_path,
            "svg_code": None,
            "description": description or None,
            "output_path": saved_path,
            "message": message,
            "asset_type": self.asset_type,
            "file_format": file_format,
            "aspect_ratio": self._compute_aspect_ratio(content, saved_path),
        }

    def _search_specific_libraries(self, name: str, max_candidates: int) -> list[str]:
        all_candidates = []
        seen = set()
        per_lib = max(1, max_candidates // len(COMPANY_LOGO_LIBRARIES))
        for lib in COMPANY_LOGO_LIBRARIES:
            results = search_icons(name_query=name, library=lib, max_results=per_lib)
            for icon_name in results.get("highPriority", []) + results.get("mediumPriority", []):
                if icon_name not in seen:
                    seen.add(icon_name)
                    all_candidates.append(icon_name)
        return all_candidates[:max_candidates]

    # --- Abstract method implementations (required by BaseAssetProvider) ---

    async def search_candidates(self, keywords: str, art_style: str, max_candidates: int) -> list[str]:
        return []

    def get_asset_content(self, icon_name: str) -> str | None:
        return ""

    async def _pick_best_visual(self, content_map: dict[str, str], description: str, name: str) -> tuple[str | None, str]:
        return None, ""

"""Fetch images from URLs and return a description for each. Extracted from the deleted MCP controller."""
import base64
import re
import time

import httpx

from scripts.logging_config import get_utility_logger
from scripts.utility.short_agent import ShortAgent
from scripts.utility.prompt_loader import get_mcp_prompt

logger = get_utility_logger('tools.describe_images_tool')


async def describe_images(image_urls: list[str]) -> dict:
    """Return {url: description} for each input URL."""
    start_time = time.time()
    logger.info(f"[DESCRIBE_IMAGES] Request: {len(image_urls)} URLs")

    if len(image_urls) > 10:
        image_urls = image_urls[:10]
        logger.warning("[DESCRIBE_IMAGES] Truncated to 10 URLs")

    results: dict[str, str] = {}
    images = []
    valid_urls = []
    svg_entries: list[tuple[str, str]] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for url in image_urls:
            try:
                response = await client.get(url)
                response.raise_for_status()
                raw = response.content
                is_svg = "svg" in response.headers.get("content-type", "") or url.lower().endswith(".svg")
                if is_svg:
                    svg_entries.append((url, response.text))
                    logger.info(f"[DESCRIBE_IMAGES] SVG detected, passing as text: {url}")
                else:
                    b64 = base64.b64encode(raw).decode("utf-8")
                    media_type = "image/png" if raw[:4] == b'\x89PNG' else "image/jpeg"
                    images.append({"data": b64, "media_type": media_type})
                    valid_urls.append(url)
            except Exception as e:
                logger.warning(f"[DESCRIBE_IMAGES] Failed to fetch {url}: {e}")
                results[url] = f"Error: could not fetch image ({e})"

    agent = ShortAgent(
        name="describe_images",
        model="sonnet",
        system_prompt=get_mcp_prompt("describe_images"),
    )

    if valid_urls:
        url_list = "\n".join(f"{i+1}. {u}" for i, u in enumerate(valid_urls))
        prompt = (
            f"Above are {len(valid_urls)} images. Their URLs in order are:\n{url_list}\n\n"
            f"For each image, describe what you see.\n"
            f"Respond in the format specified in your system prompt."
        )
        raw = (await agent.ask_with_images(prompt, images, "describe")).strip()
        for i, url in enumerate(valid_urls):
            match = re.search(rf"IMAGE\s+{i+1}\s*:\s*(.+)", raw, re.IGNORECASE)
            results[url] = match.group(1).strip() if match else (raw if len(valid_urls) == 1 else "Description not parsed")

    for svg_url, svg_code in svg_entries:
        svg_prompt = (
            f"Below is the SVG code for an image. Describe what this SVG depicts.\n"
            f"Respond with a single line description.\n\n"
            f"```svg\n{svg_code}\n```"
        )
        raw = (await agent.ask(svg_prompt, "describe_svg")).strip()
        results[svg_url] = raw

    elapsed = time.time() - start_time
    logger.info(f"[DESCRIBE_IMAGES] Complete: {len(results)} results in {elapsed*1000:.2f}ms")
    return results

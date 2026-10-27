"""Adult-only public metadata recommender Actor."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

from apify import Actor, Event
from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
from crawlee.router import Router

router = Router[BeautifulSoupCrawlingContext]()
items: dict[str, dict[str, Any]] = {}
abort_requested = False

MINOR_TERMS = re.compile(r"\b(?:child|children|kid|kids|teen|teens|minor|underage|schoolgirl|schoolboy)\b", re.I)


def parse_number(value: str | None) -> float:
    if not value:
        return 0.0
    cleaned = value.lower().replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*([kmb])?", cleaned)
    if not match:
        return 0.0
    number = float(match.group(1))
    multiplier = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(match.group(2), 1)
    return number * multiplier


def first_text(card: Any, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        element = card.select_one(selector)
        if element:
            text = element.get_text(" ", strip=True)
            if text:
                return text
    return ""


def adult_safe(title: str, url: str) -> bool:
    return not MINOR_TERMS.search(f"{title} {url}")


def extract_card(card: Any, page_url: str) -> dict[str, Any] | None:
    link = card.select_one("a[href]")
    title = first_text(card, (".title", "[data-title]", "[itemprop='name']", "h2", "h3"))
    if not link or not title:
        return None

    url = urljoin(page_url, link.get("href", "").strip())
    if not url.startswith(("http://", "https://")) or not adult_safe(title, url):
        return None

    rating_text = first_text(card, (".rating", "[data-rating]", "[itemprop='ratingValue']"))
    views_text = first_text(card, (".views", ".view-count", "[data-views]"))
    rating = min(max(parse_number(rating_text) / (100 if parse_number(rating_text) > 5 else 1), 0.0), 1.0)
    views = int(parse_number(views_text))
    return {
        "title": title,
        "url": url,
        "views": views,
        "rating": round(rating, 4),
    }


def score(item: Mapping[str, Any]) -> float:
    # Engagement is logarithmic so highly viewed items do not dominate quality.
    return round(float(item["rating"]) * 0.75 + min(math.log10(int(item["views"]) + 1) / 8, 1) * 0.25, 4)


@router.default_handler
async def default_handler(context: BeautifulSoupCrawlingContext) -> None:
    Actor.log.info(f"Scraping public metadata from {context.request.url}")
    for card in context.soup.select(".video-card, .video, .item, article, [data-video-card]"):
        item = extract_card(card, context.request.url)
        if item:
            item["score"] = score(item)
            items[item["url"]] = item
    await context.enqueue_links(selector="a.next, a[rel='next']")


async def handle_aborting() -> None:
    global abort_requested
    abort_requested = True
    Actor.log.warning("Abort requested; finishing without starting new work.")


async def main() -> None:
    global items
    Actor.on(Event.ABORTING, handle_aborting)
    async with Actor:
        user_input = await Actor.get_input() or {}
        start_urls = user_input.get("start_urls", [])
        top_n = int(user_input.get("top_n", 10))
        max_pages = int(user_input.get("max_pages", 5))
        if not start_urls:
            raise ValueError("start_urls must contain at least one listing URL.")
        if top_n < 1 or max_pages < 1:
            raise ValueError("top_n and max_pages must be at least 1.")

        items = {}
        crawler = BeautifulSoupCrawler(
            max_requests_per_crawl=max_pages,
            respect_robots_txt_file=True,
        )
        crawler.router = router
        await crawler.run(start_urls)

        recommendations = sorted(items.values(), key=lambda item: item["score"], reverse=True)[:top_n]
        for rank, item in enumerate(recommendations, start=1):
            item["rank"] = rank
            await Actor.push_data(item)
        Actor.log.info(f"Stored {len(recommendations)} adult-only recommendations.")
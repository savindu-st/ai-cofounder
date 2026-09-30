"""Web Page Scraper and Source Parser.

Uses httpx and BeautifulSoup to parse competitor landing pages, extracting
pricing tiers, feature lists, value propositions, and company taglines.
Designed with strict timeouts, content truncation, and robust error recovery.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AI-CoFounder-ResearchBot/1.0"


@dataclass
class ParsedPage:
    """Structured extraction from a target competitor webpage."""
    url: str
    title: str = ""
    tagline: str = ""
    pricing_tiers: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    raw_text: str = ""
    fetch_success: bool = False
    error_message: Optional[str] = None


class SourceParser:
    """Lightweight asynchronous HTML extractor for competitor landing pages."""

    def __init__(self, timeout_seconds: float = 8.0, max_content_chars: int = 4000):
        self.timeout = timeout_seconds
        self.max_content_chars = max_content_chars

    async def parse_page(self, url: str) -> ParsedPage:
        """Fetches and parses a webpage, returning structured competitor intelligence."""
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return ParsedPage(url=url, fetch_success=False, error_message="Invalid URL format")

        try:
            import httpx
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            async with httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
                verify=False
            ) as client:
                response = await client.get(url)
                if response.status_code >= 400:
                    return ParsedPage(
                        url=url,
                        fetch_success=False,
                        error_message=f"HTTP status {response.status_code}"
                    )

                html_content = response.text
                return self.extract_from_html(html_content, url)

        except Exception as e:
            logger.debug(f"[SourceParser] Failed to parse page {url}: {e}")
            return ParsedPage(url=url, fetch_success=False, error_message=str(e))

    def extract_from_html(self, html: str, url: str) -> ParsedPage:
        """Parses raw HTML string with BeautifulSoup and extracts semantic elements."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Remove noise scripts, styles, iframes, SVGs
            for tag in soup(["script", "style", "noscript", "iframe", "svg", "header", "footer", "nav"]):
                tag.decompose()

            # 1. Page Title
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            # 2. Tagline (meta description or og:description or hero h1)
            tagline = self._extract_tagline(soup)

            # 3. Pricing Tiers
            pricing_tiers = self._extract_pricing(soup)

            # 4. Features
            features = self._extract_features(soup)

            # 5. Cleaned Body Text
            body_text = soup.get_text(separator=" ", strip=True)
            body_text = re.sub(r"\s+", " ", body_text)
            truncated_text = body_text[:self.max_content_chars]

            return ParsedPage(
                url=url,
                title=title,
                tagline=tagline,
                pricing_tiers=pricing_tiers,
                features=features,
                raw_text=truncated_text,
                fetch_success=True
            )

        except Exception as e:
            return ParsedPage(url=url, fetch_success=False, error_message=f"HTML parsing error: {e}")

    def _extract_tagline(self, soup) -> str:
        """Extracts representative company tagline."""
        # Meta description check
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()

        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()

        # Hero h1 check
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(strip=True)
            if 10 <= len(h1_text) <= 180:
                return h1_text

        return ""

    def _extract_pricing(self, soup) -> List[str]:
        """Heuristically extracts pricing statements and tier patterns."""
        pricing_candidates = []
        pricing_regex = re.compile(r"(\$\s*\d+[\d,]*(\.\d{2})?|\bfree\b|\bcustom\b|\benterprise\b|/\s*mo(nth)?|/\s*yr|\bper\s+seat\b)", re.IGNORECASE)

        # Look in elements with pricing-related classes or IDs
        pricing_elements = soup.find_all(
            ["div", "section", "p", "li", "span"],
            attrs={"class": re.compile(r"price|pricing|tier|plan", re.IGNORECASE)}
        )

        for el in pricing_elements[:15]:
            text = el.get_text(separator=" ", strip=True)
            if pricing_regex.search(text) and 5 < len(text) < 120:
                clean = re.sub(r"\s+", " ", text)
                if clean not in pricing_candidates:
                    pricing_candidates.append(clean)

        # Fallback to general text matching if class matching was empty
        if not pricing_candidates:
            for text_node in soup.find_all(string=pricing_regex):
                parent_text = text_node.parent.get_text(strip=True) if text_node.parent else ""
                if 5 < len(parent_text) < 100 and parent_text not in pricing_candidates:
                    pricing_candidates.append(parent_text)
                if len(pricing_candidates) >= 5:
                    break

        return pricing_candidates[:5]

    def _extract_features(self, soup) -> List[str]:
        """Extracts bullet-pointed features from lists or feature blocks."""
        features = []

        # Find lists within feature sections
        feature_sections = soup.find_all(
            ["section", "div"],
            attrs={"class": re.compile(r"feature|benefit|capability|solution", re.IGNORECASE)}
        )

        target_containers = feature_sections if feature_sections else [soup]
        for container in target_containers:
            for li in container.find_all("li"):
                text = li.get_text(strip=True)
                if 12 <= len(text) <= 160 and text not in features:
                    features.append(text)
                if len(features) >= 10:
                    break
            if len(features) >= 10:
                break

        return features[:10]

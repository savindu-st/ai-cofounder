"""Citation and URL Validator.

Checks external source URLs for RFC compliance, reputable domain schemes,
and rejects placeholder/mock domains (e.g., example.com, test.com).
Enforces minimum diversity across distinct web hosts.
"""

from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class UrlValidation:
    """Validation result for an individual URL."""
    url: str
    is_valid_format: bool
    is_secure_https: bool
    is_placeholder: bool
    domain: str
    warning: str = ""


@dataclass
class CitationReport:
    """Comprehensive citation audit report across all source URLs."""
    total_urls: int
    valid_urls: int
    placeholder_urls: int
    unique_domains: int
    warnings: List[str] = field(default_factory=list)
    is_acceptable: bool = False


class CitationValidator:
    """Validates source URLs and domain reputation."""

    BLOCKLISTED_DOMAINS: Set[str] = {
        "example.com",
        "www.example.com",
        "example.org",
        "placeholder.test",
        "test.com",
        "mock.com",
        "localhost",
        "127.0.0.1",
        "tempuri.org"
    }

    def validate_single_url(self, url: str) -> UrlValidation:
        """Validates syntax, scheme, and domain reputation of a single URL."""
        if not url or not isinstance(url, str):
            return UrlValidation(
                url=str(url),
                is_valid_format=False,
                is_secure_https=False,
                is_placeholder=True,
                domain="",
                warning="URL is empty or non-string"
            )

        try:
            parsed = urlparse(url.strip())
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()

            if scheme not in ("http", "https") or not netloc:
                return UrlValidation(
                    url=url,
                    is_valid_format=False,
                    is_secure_https=False,
                    is_placeholder=False,
                    domain="",
                    warning=f"Invalid URL structure or missing host: {url}"
                )

            # Strip port if present
            domain = netloc.split(":")[0]

            is_placeholder = (
                domain in self.BLOCKLISTED_DOMAINS
                or domain.endswith(".test")
                or domain.endswith(".example")
            )

            is_https = scheme == "https"
            warning = "Domain is a known placeholder/mock" if is_placeholder else ""

            return UrlValidation(
                url=url,
                is_valid_format=True,
                is_secure_https=is_https,
                is_placeholder=is_placeholder,
                domain=domain,
                warning=warning
            )

        except Exception as e:
            return UrlValidation(
                url=url,
                is_valid_format=False,
                is_secure_https=False,
                is_placeholder=False,
                domain="",
                warning=f"Parse exception: {e}"
            )

    def validate_urls(self, urls: List[str]) -> CitationReport:
        """Audits a collection of URLs and computes composite citation metrics."""
        if not urls:
            return CitationReport(
                total_urls=0,
                valid_urls=0,
                placeholder_urls=0,
                unique_domains=0,
                warnings=["Zero citation sources provided."],
                is_acceptable=False
            )

        valid_count = 0
        placeholder_count = 0
        unique_domains: Set[str] = set()
        warnings: List[str] = []

        for u in urls:
            res = self.validate_single_url(u)
            if not res.is_valid_format:
                warnings.append(f"Invalid URL format: {u}")
                continue

            if res.is_placeholder:
                placeholder_count += 1
                warnings.append(f"Rejected placeholder domain: {u}")
                continue

            valid_count += 1
            if res.domain:
                unique_domains.add(res.domain)

            if not res.is_secure_https:
                warnings.append(f"Insecure HTTP URL: {u}")

        # Requirement: At least 2 valid sources, zero placeholders, and >= 2 unique domains
        is_acceptable = (valid_count >= 2) and (placeholder_count == 0) and (len(unique_domains) >= 2)

        if valid_count < 2:
            warnings.append(f"Insufficient citation sources: required at least 2 valid URLs, found {valid_count}.")
        if len(unique_domains) < 2 and valid_count >= 2:
            warnings.append("Low source diversity: all citations originate from the same single domain.")

        return CitationReport(
            total_urls=len(urls),
            valid_urls=valid_count,
            placeholder_urls=placeholder_count,
            unique_domains=len(unique_domains),
            warnings=warnings,
            is_acceptable=is_acceptable
        )

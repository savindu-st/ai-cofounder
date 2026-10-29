"""Evidence Grounding and Factual Cross-Reference Validator.

Audits factual market claims and trends against provided source citations.
Flags ungrounded or speculative assertions as unsupported claims.
"""

from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class EvidenceReport:
    """Report detailing factual claim grounding and unsupported claims."""
    total_claims: int
    grounded_claims: int
    unsupported_claims: List[str] = field(default_factory=list)
    grounding_score: float = 0.0
    is_acceptable: bool = False


class EvidenceValidator:
    """Validates that market claims are attributed to verified source citations."""

    def validate(
        self,
        supporting_evidence: List[str],
        market_trends: List[str],
        source_urls: List[str]
    ) -> EvidenceReport:
        """Cross-references claims against known source URLs and domain names."""
        all_claims = [c.strip() for c in (supporting_evidence + market_trends) if c and c.strip()]

        if not all_claims:
            return EvidenceReport(
                total_claims=0,
                grounded_claims=0,
                unsupported_claims=["Zero factual evidence or market trends provided for verification."],
                grounding_score=0.0,
                is_acceptable=False
            )

        # Extract domain stems and full URLs for citation matching
        valid_stems: Set[str] = set()
        for u in source_urls:
            try:
                parsed = urlparse(u.strip())
                if parsed.netloc:
                    domain = parsed.netloc.lower()
                    # e.g. "market-benchmarks.org" -> "market-benchmarks"
                    parts = domain.split(".")
                    stem = parts[-2] if len(parts) >= 2 else domain
                    if len(stem) > 3:
                        valid_stems.add(stem)
                valid_stems.add(u.strip().lower())
            except Exception:
                pass

        grounded_count = 0
        unsupported: List[str] = []

        for claim in all_claims:
            claim_lower = claim.lower()

            # A claim is considered grounded if:
            # 1. It directly mentions one of the source URLs, OR
            # 2. It references a valid domain stem (e.g. "report from global-research-metrics"), OR
            # 3. If there are valid source_urls present and the claim is in supporting_evidence which cites sources
            is_grounded = False
            for stem in valid_stems:
                if stem in claim_lower:
                    is_grounded = True
                    break

            # Fallback heuristic: If the claim contains words like "report", "source", "survey", "data", "citation",
            # and source_urls is non-empty with legitimate domains
            if not is_grounded and source_urls:
                if any(kw in claim_lower for kw in ("report", "source", "benchmarks", "survey", "published", "cited", "http")):
                    is_grounded = True

            if is_grounded:
                grounded_count += 1
            else:
                unsupported.append(f"Ungrounded market claim without verifiable source attribution: '{claim[:100]}...'")

        total = len(all_claims)
        score = round(float(grounded_count) / float(total), 2) if total > 0 else 0.0

        # Pass criteria: grounding score >= 0.70 and no more than 1 unsupported claim
        is_acceptable = (score >= 0.70) and (len(unsupported) == 0)

        return EvidenceReport(
            total_claims=total,
            grounded_claims=grounded_count,
            unsupported_claims=unsupported,
            grounding_score=score,
            is_acceptable=is_acceptable
        )

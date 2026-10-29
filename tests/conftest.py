"""Shared pytest configuration.

Forces deterministic, offline execution by default so the suite does not depend
on external LLM or search provider credentials. Set AICOUNTER_LIVE_TESTS=1 to
opt into live provider integrations.
"""

import os

if os.getenv("AICOUNTER_LIVE_TESTS", "").lower() not in ("1", "true", "yes"):
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "TAVILY_API_KEY"):
        os.environ.pop(key, None)
    os.environ["MOCK_SEARCH"] = "true"

"""Rotten Tomatoes command for Jarvis.

Search for movies and TV shows, get Tomatometer scores, and browse
what's in theaters or trending on streaming.

Scrapes the RT website directly — no API key required.
"""

import re
import json
from typing import Any, List

import httpx

from jarvis_command_sdk import (
    CommandExample,
    CommandResponse,
    FastPathPattern,
    IJarvisCommand,
    JarvisParameter,
    PreRouteResult,
    RequestInformation,
)


# --- Pre-route patterns ---
# Only the "in_theaters" action is reliably pre-routable — the "search"
# action needs the LLM to extract the movie title from natural utterances.
_IN_THEATERS_RE = re.compile(
    r"^\s*(?:"
    r"what(?:'?s|\s+is)?\s+(?:new\s+)?in\s+theaters?(?:\s+(?:right\s+now|now|this\s+week))?"
    r"|what\s+movies?\s+are\s+(?:in\s+theaters?|out)(?:\s+(?:right\s+now|now|this\s+week))?"
    r"|what'?s\s+(?:out|playing)\s+(?:in\s+theaters?|at\s+the\s+(?:movies?|theater)|right\s+now|now)"
    r"|in\s+theaters?(?:\s+(?:right\s+)?now)?"
    r"|movies?\s+in\s+theaters?"
    r"|what'?s\s+playing\s+at\s+the\s+(?:movies?|theater)"
    r"|new\s+in\s+theaters?"
    r")\s*[?.!]*$",
    re.IGNORECASE,
)

RT_BASE = "https://www.rottentomatoes.com"
REQUEST_TIMEOUT = 10.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def _fetch(url: str, params: dict | None = None) -> str:
    """Fetch a page from Rotten Tomatoes."""
    resp = httpx.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def search_rt(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search RT and extract results from the search page HTML attributes."""
    html = _fetch(f"{RT_BASE}/search", params={"search": query})

    results: list[dict[str, Any]] = []

    # Parse <search-page-media-row> elements with their attributes
    rows = re.findall(
        r'<search-page-media-row\s(.*?)</search-page-media-row>',
        html,
        re.DOTALL,
    )

    for row in rows[:limit]:
        # Extract attributes
        title_match = re.search(r'data-qa="info-name"[^>]*>\s*([^<]+)', row)
        score_match = re.search(r'tomatometer-score="(\d+)"', row)
        certified = re.search(r'tomatometer-is-certified="(true|false)"', row)
        year_match = re.search(r'release-year="(\d{4})"', row)
        cast_match = re.search(r'cast="([^"]*)"', row)
        url_match = re.search(r'href="(https://www\.rottentomatoes\.com/[mt]/[^"]+)"', row)

        title = title_match.group(1).strip() if title_match else "Unknown"
        score = int(score_match.group(1)) if score_match else None
        is_certified = certified.group(1) == "true" if certified else False
        year = int(year_match.group(1)) if year_match else None
        cast = cast_match.group(1).split(",") if cast_match and cast_match.group(1) else []
        url = url_match.group(1) if url_match else None

        # Determine type from URL
        media_type = "tv" if url and "/tv/" in url else "movie"

        results.append({
            "type": media_type,
            "title": title,
            "year": year,
            "tomatometer": score,
            "certified_fresh": is_certified,
            "cast": [c.strip() for c in cast[:3]],
            "url": url,
        })

    return results


def get_movie_detail(slug: str) -> dict[str, Any] | None:
    """Fetch detailed info from a movie page using JSON-LD data."""
    try:
        html = _fetch(f"{RT_BASE}/m/{slug}")
    except httpx.HTTPStatusError:
        return None

    # Extract JSON-LD
    ld_match = re.search(
        r'<script type="application/ld\+json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not ld_match:
        return None

    try:
        data = json.loads(ld_match.group(1))
    except json.JSONDecodeError:
        return None

    # Extract rating info
    rating = data.get("aggregateRating", {})

    return {
        "title": data.get("name", ""),
        "description": data.get("description", ""),
        "tomatometer": int(rating.get("ratingValue", 0)) if rating.get("ratingValue") else None,
        "review_count": rating.get("reviewCount"),
        "content_rating": data.get("contentRating"),
        "genres": data.get("genre", []),
        "director": [d.get("name", "") for d in data.get("director", [])],
        "cast": [a.get("name", "") for a in data.get("actor", [])][:5],
        "release_date": data.get("dateCreated"),
        "url": data.get("url"),
    }


def browse_in_theaters() -> list[dict[str, Any]]:
    """Scrape the 'In Theaters' section from the RT homepage."""
    html = _fetch(f"{RT_BASE}/browse/movies_in_theaters/sort:popular")

    results: list[dict[str, Any]] = []
    # Look for tile elements with scores
    tiles = re.findall(
        r'<a[^>]*href="(/m/[^"]+)"[^>]*>.*?'
        r'<span[^>]*class="[^"]*p--small[^"]*"[^>]*>\s*([^<]+)',
        html,
        re.DOTALL,
    )

    # Fallback: parse search-page-media-row if present
    if not tiles:
        rows = re.findall(
            r'<search-page-media-row\s(.*?)</search-page-media-row>',
            html,
            re.DOTALL,
        )
        for row in rows[:10]:
            title_match = re.search(r'data-qa="info-name"[^>]*>\s*([^<]+)', row)
            score_match = re.search(r'tomatometer-score="(\d+)"', row)
            url_match = re.search(r'href="(https://www\.rottentomatoes\.com/m/[^"]+)"', row)
            if title_match:
                results.append({
                    "title": title_match.group(1).strip(),
                    "tomatometer": int(score_match.group(1)) if score_match else None,
                    "url": url_match.group(1) if url_match else None,
                })

    return results


class RottenTomatoesCommand(IJarvisCommand):

    @property
    def command_name(self) -> str:
        return "rotten_tomatoes"

    @property
    def description(self) -> str:
        return (
            "Search Rotten Tomatoes for movie and TV show ratings. "
            "Returns Tomatometer scores, cast info, and Certified Fresh status."
        )

    @property
    def keywords(self) -> List[str]:
        return [
            "movie", "movies", "film", "rating", "ratings", "rotten tomatoes",
            "tomatometer", "review", "reviews", "what to watch", "in theaters",
            "streaming", "tv show", "audience score", "fresh", "certified fresh",
        ]

    @property
    def parameters(self) -> list:
        return [
            JarvisParameter(
                "query", "string", required=False,
                description="Movie or TV show title to search for",
            ),
            JarvisParameter(
                "action", "string", required=False,
                description="What to do: 'search' (default) or 'in_theaters'",
                enum_values=["search", "in_theaters"],
            ),
        ]

    @property
    def required_secrets(self) -> list:
        return []

    @property
    def rules(self) -> list:
        return [
            "Default action is 'search' when a query is provided",
            "If no query but the user asks 'what's in theaters' or 'what's new', use 'in_theaters'",
        ]

    def generate_prompt_examples(self) -> List[CommandExample]:
        return [
            CommandExample(
                "what's the rating for The Shawshank Redemption",
                {"query": "The Shawshank Redemption", "action": "search"},
                is_primary=True,
            ),
            CommandExample(
                "is Dune 2 any good",
                {"query": "Dune Part Two", "action": "search"},
            ),
            CommandExample(
                "what movies are in theaters right now",
                {"action": "in_theaters"},
            ),
        ]

    def generate_adapter_examples(self) -> List[CommandExample]:
        return self.generate_prompt_examples() + [
            CommandExample(
                "how did Oppenheimer do on rotten tomatoes",
                {"query": "Oppenheimer", "action": "search"},
            ),
            CommandExample(
                "is The Bear worth watching",
                {"query": "The Bear", "action": "search"},
            ),
        ]

    # ------------------------------------------------------------------
    # Fast-path patterns — bypass LLM for "in theaters" only. Search
    # queries need LLM-extracted titles and stay on the slow path.
    # ------------------------------------------------------------------
    @property
    def fast_path_patterns(self) -> List[FastPathPattern]:
        return [
            FastPathPattern(
                id="rotten_tomatoes.in_theaters",
                description="Bypass LLM for 'what's in theaters' / 'what movies are out'",
                example="what movies are in theaters",
                regex=_IN_THEATERS_RE.pattern,
                handler="_fp_in_theaters",
            ),
        ]

    def _fp_in_theaters(self, match, voice_command: str) -> PreRouteResult | None:
        return PreRouteResult(arguments={"action": "in_theaters"})

    def run(self, request_info: RequestInformation, **kwargs) -> CommandResponse:
        action = kwargs.get("action", "search")
        query = kwargs.get("query")

        try:
            if action == "search":
                if not query:
                    return CommandResponse.error_response(
                        "What movie or show would you like to look up?"
                    )
                results = search_rt(query)
                if not results:
                    return CommandResponse.success_response({
                        "message": f"No results found for '{query}' on Rotten Tomatoes.",
                        "query": query,
                        "results": [],
                    })
                return CommandResponse.success_response({
                    "query": query,
                    "results": results,
                    "result_count": len(results),
                })

            elif action == "in_theaters":
                results = browse_in_theaters()
                return CommandResponse.success_response({
                    "category": "in_theaters",
                    "results": results,
                    "result_count": len(results),
                })

            else:
                return CommandResponse.error_response(f"Unknown action: {action}")

        except httpx.HTTPStatusError as e:
            return CommandResponse.error_response(
                f"Rotten Tomatoes error: HTTP {e.response.status_code}"
            )
        except httpx.ConnectError:
            return CommandResponse.error_response(
                "Could not connect to Rotten Tomatoes. Check your internet connection."
            )
        except Exception as e:
            return CommandResponse.error_response(f"Error: {str(e)}")

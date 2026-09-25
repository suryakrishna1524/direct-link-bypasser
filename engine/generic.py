import re
import urllib.parse
import httpx
from typing import List, Dict, Any, Tuple

class GenericRedirectBypasser:
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    @staticmethod
    def extract_meta_refresh(html: str, current_url: str) -> str | None:
        match = re.search(r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*content=["\']\s*\d+\s*;\s*url=([^"\']+)["\']', html, re.I)
        if not match:
            match = re.search(r'<meta[^>]*content=["\']\s*\d+\s*;\s*url=([^"\']+)["\'][^>]*http-equiv=["\']refresh["\']', html, re.I)
        if match:
            raw_url = match.group(1).strip()
            return urllib.parse.urljoin(current_url, raw_url)
        return None

    @staticmethod
    def extract_js_redirect(html: str, current_url: str) -> str | None:
        patterns = [
            r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
            r'location\.replace\s*\(\s*["\']([^"\']+)["\']\s*\)',
            r'location\.href\s*=\s*["\']([^"\']+)["\']',
            r'window\.location\.assign\s*\(\s*["\']([^"\']+)["\']\s*\)',
        ]
        for p in patterns:
            match = re.search(p, html, re.I)
            if match:
                raw_url = match.group(1).strip()
                if raw_url.startswith('http://') or raw_url.startswith('https://') or raw_url.startswith('/'):
                    return urllib.parse.urljoin(current_url, raw_url)
        return None

    @classmethod
    async def resolve(cls, initial_url: str, max_hops: int = 15) -> Tuple[str, List[Dict[str, Any]]]:
        hops = []
        current_url = initial_url
        visited = set()

        async with httpx.AsyncClient(headers=cls.DEFAULT_HEADERS, follow_redirects=False, timeout=12.0) as client:
            for step in range(max_hops):
                if current_url in visited:
                    break
                visited.add(current_url)

                try:
                    resp = await client.get(current_url)
                except Exception as ex:
                    hops.append({
                        "step": step + 1,
                        "url": current_url,
                        "status": "error",
                        "error": str(ex)
                    })
                    break

                hops.append({
                    "step": step + 1,
                    "url": current_url,
                    "status_code": resp.status_code,
                    "type": "http"
                })

                # 1. HTTP 3xx Redirect
                if resp.is_redirect:
                    location = resp.headers.get("Location")
                    if location:
                        current_url = urllib.parse.urljoin(current_url, location)
                        continue

                # If 200 OK, check HTML body for client-side meta/JS redirects
                html = resp.text
                meta_url = cls.extract_meta_refresh(html, current_url)
                if meta_url and meta_url != current_url and meta_url not in visited:
                    hops[-1]["type"] = "meta_refresh"
                    current_url = meta_url
                    continue

                js_url = cls.extract_js_redirect(html, current_url)
                if js_url and js_url != current_url and js_url not in visited:
                    hops[-1]["type"] = "js_redirect"
                    current_url = js_url
                    continue

                # No further redirects found
                break

        return current_url, hops

import re
import urllib.parse
import httpx
from typing import Dict, Any, Tuple

class SpecializedShorteners:
    @staticmethod
    def matches(url: str) -> bool:
        domain = urllib.parse.urlparse(url).netloc.lower()
        known = [
            'bit.ly', 'tinyurl.com', 'cutt.ly', 't.co', 'is.gd', 'v.gd',
            'rebrand.ly', 'shorturl.at', 'bl.ink', 'ouo.io', 'ouo.press',
            'adf.ly', 'mega.nz', 'git.io'
        ]
        return any(domain.endswith(k) for k in known)

    @classmethod
    async def resolve(cls, url: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'},
            follow_redirects=True,
            timeout=10.0
        ) as client:
            resp = await client.get(url)
            final_url = str(resp.url)
            hops = [{"url": str(r.url), "status": r.status_code} for r in resp.history]
            hops.append({"url": final_url, "status": resp.status_code})
            
            return {
                "success": True,
                "final_url": final_url,
                "hops": hops,
                "stages_bypassed": len(hops)
            }

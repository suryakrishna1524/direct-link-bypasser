import time
import urllib.parse
from typing import Dict, Any, List
from .query_decoder import QueryDecoder
from .generic import GenericRedirectBypasser
from .wpsafelink import WPSafeLinkBypasser
from .shorteners import SpecializedShorteners

class BypassManager:
    @classmethod
    async def bypass_url(cls, raw_url: str) -> Dict[str, Any]:
        url = raw_url.strip()
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        start_time = time.time()

        # 1. Instant Token / Query Extraction (0s latency)
        instant_target = QueryDecoder.extract_from_url(url)
        if instant_target and instant_target != url:
            duration = round(time.time() - start_time, 3)
            return {
                "success": True,
                "original_url": url,
                "final_url": instant_target,
                "method": "Instant Query / Base64 Token Decoded",
                "hops_bypassed": 1,
                "hops": [
                    {"step": 1, "url": url, "stage": "Input URL"},
                    {"step": 2, "url": instant_target, "stage": "Decoded Target URL"}
                ],
                "duration_seconds": duration,
                "time_saved_seconds": 30
            }

        # 2. Multi-tier Ad / SafeLink shorteners (ShortXLinks, WPSafeLink, SoftURL, etc.)
        if WPSafeLinkBypasser.matches(url):
            try:
                res = await WPSafeLinkBypasser.resolve(url)
                if res.get("final_url") and res["final_url"] != url:
                    res.update({
                        "original_url": url,
                        "method": "WPSafeLink Multi-Tier Recursive Solver"
                    })
                    return res
            except Exception as e:
                return {
                    "success": False,
                    "original_url": url,
                    "error": f"SafeLink Solver error: {str(e)}",
                    "duration_seconds": round(time.time() - start_time, 3)
                }

        # 3. Known Direct Shorteners (Bitly, Tinyurl, etc.)
        if SpecializedShorteners.matches(url):
            try:
                res = await SpecializedShorteners.resolve(url)
                if res.get("final_url") and res["final_url"] != url:
                    duration = round(time.time() - start_time, 3)
                    res.update({
                        "original_url": url,
                        "method": "Direct Shortener Resolver",
                        "duration_seconds": duration,
                        "time_saved_seconds": 10
                    })
                    return res
            except Exception:
                pass

        # 4. Universal Generic Redirect + JS Resolver
        try:
            final_url, hops = await GenericRedirectBypasser.resolve(url)
            duration = round(time.time() - start_time, 3)
            if final_url == url:
                return {
                    "success": False,
                    "original_url": url,
                    "final_url": url,
                    "error": "No further redirects found. The URL is already direct or protected.",
                    "duration_seconds": duration
                }

            return {
                "success": True,
                "original_url": url,
                "final_url": final_url,
                "method": "Generic HTTP / Meta / JS Redirect Resolver",
                "hops_bypassed": max(1, len(hops) - 1),
                "hops": hops,
                "duration_seconds": duration,
                "time_saved_seconds": (len(hops) - 1) * 5
            }
        except Exception as e:
            return {
                "success": False,
                "original_url": url,
                "error": str(e),
                "duration_seconds": round(time.time() - start_time, 3)
            }

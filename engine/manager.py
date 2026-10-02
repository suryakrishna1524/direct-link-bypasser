import time
import urllib.parse
from typing import Dict, Any, List
from .query_decoder import QueryDecoder
from .generic import GenericRedirectBypasser
from .wpsafelink import WPSafeLinkBypasser
from .shorteners import SpecializedShorteners
from .db import BypassDatabase

class BypassManager:
    @classmethod
    async def bypass_url(cls, raw_url: str, force: bool = False) -> Dict[str, Any]:
        url = raw_url.strip()
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        start_time = time.time()

        # 0. Instant Database / Cloud Cache Lookup (unless force refresh requested)
        if not force:
            try:
                cached = await BypassDatabase.get_cached_bypass(url)
                if cached and cached.get("final_url") and cached["final_url"] != url:
                    duration = round(time.time() - start_time, 4)
                    cached.update({
                        "success": True,
                        "cached": True,
                        "original_url": url,
                        "duration_seconds": duration,
                        "verified_destination": cached.get("verified", True),
                        "method": "Instant Community Cache (Previously Bypassed)"
                    })
                    return cached
            except Exception:
                pass
        else:
            # Clear old cache entry on force refresh
            try:
                await BypassDatabase.delete_cached_bypass(url)
            except Exception:
                pass

        # 1. Instant Token / Query Extraction (0s latency)
        instant_target = QueryDecoder.extract_from_url(url)
        if instant_target and instant_target != url:
            duration = round(time.time() - start_time, 3)
            is_confirmed = BypassDatabase.is_confirmed_destination(instant_target)
            res = {
                "success": True,
                "original_url": url,
                "final_url": instant_target,
                "method": "Instant Query / Base64 Token Decoded",
                "hops_bypassed": 1,
                "verified_destination": is_confirmed,
                "hops": [
                    {"step": 1, "url": url, "stage": "Input URL"},
                    {"step": 2, "url": instant_target, "stage": "Decoded Target URL"}
                ],
                "duration_seconds": duration,
                "time_saved_seconds": 30
            }
            if is_confirmed:
                await BypassDatabase.set_cached_bypass(url, instant_target, res["hops"], res["method"], False, 30, user_verified=False)
            return res

        # 2. Multi-tier Ad / SafeLink shorteners (ShortXLinks, WPSafeLink, SoftURL, etc.)
        if WPSafeLinkBypasser.matches(url):
            try:
                res = await WPSafeLinkBypasser.resolve(url)
                res.setdefault("original_url", url)
                if res.get("success"):
                    res.update({
                        "method": "WPSafeLink Multi-Tier Recursive Solver"
                    })
                    final_url = res.get("final_url")
                    is_confirmed = BypassDatabase.is_confirmed_destination(final_url)
                    res["verified_destination"] = is_confirmed
                    
                    # Cache to DB so subsequent requests are 0ms instant
                    if final_url and final_url != url:
                        await BypassDatabase.set_cached_bypass(
                            url,
                            final_url,
                            res.get("hops", []),
                            res["method"],
                            res.get("intermediate", False),
                            res.get("time_saved_seconds", 60),
                            user_verified=is_confirmed
                        )
                    return res
                elif res.get("error"):
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
                    final_url = res["final_url"]
                    is_confirmed = BypassDatabase.is_confirmed_destination(final_url)
                    res.update({
                        "original_url": url,
                        "method": "Direct Shortener Resolver",
                        "duration_seconds": duration,
                        "time_saved_seconds": 10,
                        "verified_destination": is_confirmed
                    })
                    if is_confirmed:
                        await BypassDatabase.set_cached_bypass(
                            url,
                            final_url,
                            res.get("hops", []),
                            res["method"],
                            False,
                            10,
                            user_verified=False
                        )
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

            time_saved = max(10, (len(hops) - 1) * 5)
            method_desc = "Generic HTTP / Meta / JS Redirect Resolver"
            is_confirmed = BypassDatabase.is_confirmed_destination(final_url)
            res = {
                "success": True,
                "original_url": url,
                "final_url": final_url,
                "method": method_desc,
                "hops_bypassed": max(1, len(hops) - 1),
                "hops": hops,
                "duration_seconds": duration,
                "time_saved_seconds": time_saved,
                "verified_destination": is_confirmed
            }
            if is_confirmed:
                await BypassDatabase.set_cached_bypass(url, final_url, hops, method_desc, False, time_saved, user_verified=False)
            return res
        except Exception as e:
            return {
                "success": False,
                "original_url": url,
                "error": str(e),
                "duration_seconds": round(time.time() - start_time, 3)
            }

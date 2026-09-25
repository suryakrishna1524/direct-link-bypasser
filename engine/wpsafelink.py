import re
import urllib.request
import urllib.parse
import base64
import json
import asyncio
import time
import http.cookiejar
from typing import Dict, Any, List

KNOWN_SHORTENER_HOSTS = [
    'shortxlinks.com', 'softurl.in', 'droplink', 'adlinkfly', 'safelink',
    'trickscolony.com', 'ibapam.in', 'evloadercarrompool.com'
]

class WPSafeLinkBypasser:
    """
    Optimized high-speed multi-tier WPSafeLink & AdLinkFly chained shortener solver.
    Eliminates all client-side countdown delays and syncs with the exact minimum
    server-side security cooldown (30.0s) for maximum throughput.
    """
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    @classmethod
    def matches(cls, url: str) -> bool:
        domain = urllib.parse.urlparse(url).netloc.lower()
        return any(k in domain or k in url.lower() for k in KNOWN_SHORTENER_HOSTS)

    @classmethod
    def is_intermediate_shortener(cls, url: str) -> bool:
        domain = urllib.parse.urlparse(url).netloc.lower()
        return any(k in domain for k in ['shortxlinks.com', 'softurl.in', 'droplink', 'adlinkfly'])

    @classmethod
    def _solve_single_stage_sync(cls, shortlink: str, hops: List[Dict[str, Any]], round_num: int) -> str:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        headers = cls.DEFAULT_HEADERS
        t_start = time.time()

        hops.append({"step": len(hops) + 1, "url": shortlink, "stage": f"Round {round_num}: Initial Handshake"})
        
        # Step 1: Initial GET
        req1 = urllib.request.Request(shortlink, headers=headers)
        with opener.open(req1) as resp:
            html1 = resp.read().decode('utf-8', errors='ignore')
            url1 = resp.geturl()

        action1_m = re.search(r'action=["\']([^"\']+)["\']', html1)
        go1_m = re.search(r'name=["\']go["\']\s+value=["\']([^"\']+)["\']', html1)
        if not action1_m or not go1_m:
            return url1

        action1 = action1_m.group(1)
        go1 = go1_m.group(1)

        # Step 2: POST to Landing (Fast-Forward)
        hops.append({"step": len(hops) + 1, "url": action1, "stage": f"Round {round_num}: Layer 1 Landing"})
        data1 = urllib.parse.urlencode({'go': go1}).encode('utf-8')
        req2 = urllib.request.Request(action1, data=data1, headers={**headers, 'Referer': shortlink})
        with opener.open(req2) as resp:
            html2 = resp.read().decode('utf-8', errors='ignore')
            url2 = resp.geturl()

        action2_m = re.search(r'action=["\']([^"\']+)["\']', html2)
        newwpsafe2_m = re.search(r'name=["\']newwpsafelink["\']\s+value=["\']([^"\']+)["\']', html2)
        humanver2_m = re.search(r'name=["\']humanverification["\']\s+value=["\']([^"\']+)["\']', html2)

        if not action2_m or not newwpsafe2_m or not humanver2_m:
            return url2

        action2 = action2_m.group(1)
        newwpsafelink2 = newwpsafe2_m.group(1)
        humanver2 = humanver2_m.group(1)

        # Step 3: POST to Article 1 (Fast-Forward)
        hops.append({"step": len(hops) + 1, "url": action2, "stage": f"Round {round_num}: Layer 1 Article 1"})
        data2 = urllib.parse.urlencode({'humanverification': humanver2, 'newwpsafelink': newwpsafelink2}).encode('utf-8')
        req3 = urllib.request.Request(action2, data=data2, headers={**headers, 'Referer': action1})
        with opener.open(req3) as resp:
            html3 = resp.read().decode('utf-8', errors='ignore')
            url3 = resp.geturl()

        form3_m = re.search(r'<form[^>]*id=["\']wpsafelink-landing["\'][^>]*action=["\']([^"\']+)["\']', html3)
        newwpsafe3_m = re.search(r'name=["\']newwpsafelink["\'][^>]*value=["\']([^"\']+)["\']', html3)
        if not form3_m or not newwpsafe3_m:
            return url3

        action3 = form3_m.group(1)
        newwpsafe3 = newwpsafe3_m.group(1)

        # Step 4: POST to Article 2 (Skipping 25s JavaScript countdown instantly)
        hops.append({"step": len(hops) + 1, "url": action3, "stage": f"Round {round_num}: Bypassing 25s Layer 1 Countdown"})
        data3 = urllib.parse.urlencode({'newwpsafelink': newwpsafe3}).encode('utf-8')
        req4 = urllib.request.Request(action3, data=data3, headers={**headers, 'Referer': url3})
        with opener.open(req4) as resp:
            html4 = resp.read().decode('utf-8', errors='ignore')
            url4 = resp.geturl()

        safelink_m4 = re.search(r"window\.open\(['\"]([^'\"]*safelink_redirect=[^'\"]*)['\"]", html4)
        if not safelink_m4:
            return url4

        safelink_url4 = safelink_m4.group(1)

        # Step 5: GET to Layer 2 domain
        hops.append({"step": len(hops) + 1, "url": safelink_url4, "stage": f"Round {round_num}: Layer 2 Entry"})
        req5 = urllib.request.Request(safelink_url4, headers={**headers, 'Referer': url4})
        with opener.open(req5) as resp:
            html5 = resp.read().decode('utf-8', errors='ignore')
            url5 = resp.geturl()

        action5_m = re.search(r'action=["\']([^"\']+)["\']', html5)
        if not action5_m:
            return url5

        action5 = action5_m.group(1)
        inputs5 = dict(re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', html5))

        # Step 6: POST to Layer 2 Landing
        data5 = urllib.parse.urlencode(inputs5).encode('utf-8')
        req6 = urllib.request.Request(action5, data=data5, headers={**headers, 'Referer': url5})
        with opener.open(req6) as resp:
            html6 = resp.read().decode('utf-8', errors='ignore')
            url6 = resp.geturl()

        action6_m = re.search(r'action=["\']([^"\']+)["\']', html6)
        if not action6_m:
            return url6

        action6 = action6_m.group(1)
        inputs6 = dict(re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', html6))

        # Step 7: POST to Layer 2 Article 1
        hops.append({"step": len(hops) + 1, "url": action6, "stage": f"Round {round_num}: Layer 2 Article 1"})
        data6 = urllib.parse.urlencode(inputs6).encode('utf-8')
        req7 = urllib.request.Request(action6, data=data6, headers={**headers, 'Referer': url6})
        with opener.open(req7) as resp:
            html7 = resp.read().decode('utf-8', errors='ignore')
            url7 = resp.geturl()

        form7_m = re.search(r'<form[^>]*id=["\']wpsafelink-landing["\'][^>]*action=["\']([^"\']+)["\']', html7)
        if not form7_m:
            return url7

        action7 = form7_m.group(1)
        inputs7 = dict(re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', html7))

        # Step 8: POST to Layer 2 Article 2 (Skipping second 25s countdown instantly)
        hops.append({"step": len(hops) + 1, "url": action7, "stage": f"Round {round_num}: Bypassing 25s Layer 2 Countdown"})
        data7 = urllib.parse.urlencode(inputs7).encode('utf-8')
        req8 = urllib.request.Request(action7, data=data7, headers={**headers, 'Referer': url7})
        with opener.open(req8) as resp:
            html8 = resp.read().decode('utf-8', errors='ignore')
            url8 = resp.geturl()

        safelink_m8 = re.search(r"window\.open\(['\"]([^'\"]*safelink_redirect=[^'\"]*)['\"]", html8)
        if not safelink_m8:
            return url8

        safelink_url8 = safelink_m8.group(1)
        redir_payload8 = safelink_url8.split('safelink_redirect=')[1]
        decoded8 = base64.b64decode(redir_payload8).decode('utf-8')
        data_json8 = json.loads(decoded8)
        final_token_url = data_json8.get('safelink')

        # Precise server rate limit sync (30s required by backend timestamp)
        elapsed = time.time() - t_start
        if elapsed < 30.0:
            wait_needed = 30.0 - elapsed
            hops.append({
                "step": len(hops) + 1,
                "url": final_token_url,
                "stage": f"Round {round_num}: Rate Limit Cooldown Sync ({int(wait_needed)}s)"
            })
            time.sleep(wait_needed)

        # Step 9: Final Redemption on Shortener
        hops.append({"step": len(hops) + 1, "url": final_token_url, "stage": f"Round {round_num}: Redeeming Token on Shortener"})
        html9 = ""
        url9 = final_token_url
        for _ in range(4):
            req9 = urllib.request.Request(final_token_url, headers={**headers, 'Referer': url8})
            with opener.open(req9) as resp:
                html9 = resp.read().decode('utf-8', errors='ignore')
                url9 = resp.geturl()
            if "Too Early" not in html9:
                break
            time.sleep(2.0)

        # Step 10: /links/go AJAX
        form_m = re.search(r'<form[^>]*action=["\']([^"\']*)["\'][^>]*>(.*?)</form>', html9, re.DOTALL)
        if not form_m:
            return url9

        go_action = form_m.group(1)
        go_body = form_m.group(2)
        go_inputs = dict(re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', go_body))

        if not go_action.startswith('http'):
            go_action = urllib.parse.urljoin(url9, go_action)

        headers_ajax = dict(headers)
        headers_ajax.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': url9
        })

        go_data = urllib.parse.urlencode(go_inputs).encode('utf-8')
        req10 = urllib.request.Request(go_action, data=go_data, headers=headers_ajax)
        
        with opener.open(req10) as resp10:
            res10_text = resp10.read().decode('utf-8', errors='ignore')
            try:
                res10_json = json.loads(res10_text)
                return res10_json.get('url', url9)
            except Exception:
                return url9

    @classmethod
    def _solve_single_stage_entry(cls, start_url: str) -> Dict[str, Any]:
        hops = []
        t0 = time.time()
        resolved_url = cls._solve_single_stage_sync(start_url, hops, 1)
        duration = round(time.time() - t0, 2)
        is_intermediate = cls.is_intermediate_shortener(resolved_url) if resolved_url else False

        return {
            "success": bool(resolved_url and resolved_url != start_url),
            "final_url": resolved_url,
            "intermediate": is_intermediate,
            "hops": hops,
            "stages_bypassed": len(hops),
            "duration_seconds": duration,
            "time_saved_seconds": max(45, int(duration + 45))
        }

    @classmethod
    async def resolve(cls, start_url: str) -> Dict[str, Any]:
        return await asyncio.to_thread(cls._solve_single_stage_entry, start_url)

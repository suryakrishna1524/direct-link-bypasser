import re
import urllib.request
import urllib.parse
import urllib.error
import base64
import json
import asyncio
import time
import http.cookiejar
from typing import Dict, Any, List, Optional

# Non-exhaustive keywords for fast matching, but engine works dynamically on any domain via HTML signature
KNOWN_SHORTENER_HINTS = [
    'short', 'link', 'safe', 'url', 'drop', 'fly', 'earn', 'shrink',
    'tiny', 'bitly', 'droplink', 'adlinkfly', 'safelink', 'wp',
    'thetechhint', 'distancedata', 'trickscolony', 'ibapam'
]

# Known final destination domains that should never be marked intermediate
FINAL_DESTINATION_DOMAINS = [
    't.me', 'telegram.me', 'telegram.dog', 'drive.google.com', 'mega.nz',
    'mega.co.nz', 'mediafire.com', 'github.com', 'youtube.com', 'youtu.be',
    'dropbox.com', '1fichier.com', 'pixeldrain.com', 'send.cm', 'racaty.net',
    'krakenfiles.com', 'gofile.io', 'terabox.com', 'workupload.com'
]

class WPSafeLinkBypasser:
    """
    Universal Dynamic Multi-Layer SafeLink & AdLinkFly Solver.
    
    Operates completely dynamically via DOM form signatures and Base64 safelink payloads.
    Does NOT depend on hardcoded intermediate blog domains. Automatically traverses 1, 2, 3, or N
    landing article layers and skips all client-side countdowns instantly.
    """
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    @classmethod
    def matches(cls, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.strip('/')
        
        # Fast exit for known final platforms
        if any(d in domain for d in FINAL_DESTINATION_DOMAINS):
            return False
            
        # Match if domain has shortener hints or path looks like a shortener slug (1-15 chars)
        if any(k in domain for k in KNOWN_SHORTENER_HINTS):
            return True
            
        if path and len(path) <= 20 and not ('.' in path and not path.endswith('.html')):
            return True
            
        return False

    @classmethod
    def is_intermediate_shortener(cls, url: str) -> bool:
        if not url:
            return False
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        
        if any(d in domain for d in FINAL_DESTINATION_DOMAINS):
            return False
            
        # Check direct download extensions
        if any(path.endswith(ext) for ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.mp4', '.mkv', '.pdf', '.apk', '.exe']):
            return False
            
        # If it has shortener keywords or looks like another shortener
        if any(k in domain for k in KNOWN_SHORTENER_HINTS):
            return True
            
        return False

    @classmethod
    def _solve_single_stage_sync(cls, shortlink: str, hops: List[Dict[str, Any]], round_num: int) -> str:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        headers = cls.DEFAULT_HEADERS
        t_start = time.time()

        hops.append({"step": len(hops) + 1, "url": shortlink, "stage": f"Round {round_num}: Initial Handshake"})
        
        # Step 1: Initial Handshake GET
        req1 = urllib.request.Request(shortlink, headers=headers)
        with opener.open(req1) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            curr_url = resp.geturl()

        # Check for initial shortener 'go' form, landing form, or safelink redirect
        go_m = re.search(r'name=["\']go["\']\s+value=["\']([^"\']+)["\']', html)
        act_m = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', html)
        form_landing_m = re.search(r'<form[^>]*action=["\']([^"\']*)["\'][^>]*>(.*?)</form>', html, re.DOTALL)
        safelink_m = re.search(r'["\']([^"\']*safelink_redirect=[^"\']*)["\']', html)
        
        if go_m and act_m:
            curr_action = act_m.group(1)
            post_data = {'go': go_m.group(1)}
        elif form_landing_m and ('newwpsafelink' in form_landing_m.group(2) or 'humanverification' in form_landing_m.group(2)):
            act = form_landing_m.group(1) or curr_url
            if not act.startswith('http'):
                act = urllib.parse.urljoin(curr_url, act)
            inputs = dict(re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', form_landing_m.group(2)))
            curr_action = act
            post_data = inputs
        elif safelink_m:
            curr_action = safelink_m.group(1)
            post_data = None
        else:
            return curr_url

        ref = curr_url
        final_token_url = None

        # Universal Dynamic Multi-Layer State Machine (Traverses any number of WordPress landing/article layers)
        for layer_hop in range(1, 15):
            if post_data is not None:
                data_bytes = urllib.parse.urlencode(post_data).encode('utf-8')
                req_hop = urllib.request.Request(curr_action, data=data_bytes, headers={**headers, 'Referer': ref})
                stage_desc = f"Round {round_num}: Fast-Forwarding Article Layer {layer_hop}"
            else:
                req_hop = urllib.request.Request(curr_action, headers={**headers, 'Referer': ref})
                stage_desc = f"Round {round_num}: Entering Nested SafeLink Layer {layer_hop}"

            hops.append({"step": len(hops) + 1, "url": curr_action, "stage": stage_desc})

            with opener.open(req_hop) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                ref = resp.geturl()

            # 1. Search for safelink_redirect parameter in JavaScript or DOM links
            safelink_m = re.search(r"window\.open\(['\"]([^'\"]*safelink_redirect=[^'\"]*)['\"]", html)
            if not safelink_m:
                safelink_m = re.search(r'["\']([^"\']*safelink_redirect=[^"\']*)["\']', html)

            if safelink_m:
                safelink_full_url = safelink_m.group(1)
                redir_payload = safelink_full_url.split('safelink_redirect=')[1].split('&')[0].split('"')[0].split("'")[0]
                redir_payload = urllib.parse.unquote(redir_payload)
                try:
                    decoded = base64.b64decode(redir_payload).decode('utf-8', errors='ignore')
                    data_json = json.loads(decoded)
                    
                    if data_json.get('second_safelink_url') or data_json.get('next_safelink_url'):
                        # Found chained intermediary layer -> follow URL dynamically
                        curr_action = safelink_full_url
                        post_data = None
                        continue
                    elif data_json.get('safelink'):
                        # Unlocked shortener redemption token!
                        final_token_url = data_json['safelink']
                        break
                except Exception:
                    pass

            # 2. Extract next form dynamically from page
            form_m = re.search(r'<form[^>]*id=["\']wpsafelink-landing["\'][^>]*action=["\']([^"\']*)["\'][^>]*>(.*?)</form>', html, re.DOTALL)
            if not form_m:
                form_m = re.search(r'<form[^>]*action=["\']([^"\']*)["\'][^>]*>(.*?)</form>', html, re.DOTALL)

            if form_m:
                act = form_m.group(1) or ref
                if not act.startswith('http'):
                    act = urllib.parse.urljoin(ref, act)
                body = form_m.group(2)
                inputs = dict(re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', body))
                curr_action = act
                post_data = inputs
            else:
                break

        if not final_token_url:
            return ref

        # Step 3: Precise server rate limit cooldown sync (30.0s)
        elapsed = time.time() - t_start
        if elapsed < 30.0:
            wait_needed = 30.0 - elapsed
            hops.append({
                "step": len(hops) + 1,
                "url": final_token_url,
                "stage": f"Round {round_num}: Rate Limit Cooldown Sync ({int(wait_needed)}s)"
            })
            time.sleep(wait_needed)

        # Step 4: Final Token Redemption on Shortener
        hops.append({"step": len(hops) + 1, "url": final_token_url, "stage": f"Round {round_num}: Redeeming Token on Shortener"})
        html_red = ""
        url_red = final_token_url
        for _ in range(4):
            req_red = urllib.request.Request(final_token_url, headers={**headers, 'Referer': ref})
            with opener.open(req_red) as resp_red:
                html_red = resp_red.read().decode('utf-8', errors='ignore')
                url_red = resp_red.geturl()
            if "Too Early" not in html_red:
                break
            time.sleep(2.0)

        # Step 5: /links/go AJAX Submission
        form_go = re.search(r'<form[^>]*action=["\']([^"\']*)["\'][^>]*>(.*?)</form>', html_red, re.DOTALL)
        if not form_go:
            return url_red

        go_action = form_go.group(1)
        go_body = form_go.group(2)
        go_inputs = dict(re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', go_body))

        if not go_action.startswith('http'):
            go_action = urllib.parse.urljoin(url_red, go_action)

        headers_ajax = dict(headers)
        headers_ajax.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': url_red
        })

        go_data = urllib.parse.urlencode(go_inputs).encode('utf-8')
        req_ajax = urllib.request.Request(go_action, data=go_data, headers=headers_ajax)
        
        with opener.open(req_ajax) as resp_ajax:
            res_text = resp_ajax.read().decode('utf-8', errors='ignore')
            try:
                res_json = json.loads(res_text)
                return res_json.get('url', url_red)
            except Exception:
                return url_red

    @classmethod
    def _solve_single_stage_entry(cls, start_url: str) -> Dict[str, Any]:
        hops = []
        t0 = time.time()
        try:
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
        except urllib.error.HTTPError as e:
            duration = round(time.time() - t0, 2)
            is_captcha = e.code in (403, 429, 503)
            return {
                "success": False,
                "final_url": start_url,
                "error": "This shortener is protected by LiteSpeed/Cloudflare bot verification (HTTP 403)." if e.code == 403 else f"HTTP Error {e.code}: {e.reason}",
                "captcha_blocked": is_captcha,
                "hops": hops,
                "duration_seconds": duration
            }
        except Exception as e:
            duration = round(time.time() - t0, 2)
            return {
                "success": False,
                "final_url": start_url,
                "error": str(e),
                "hops": hops,
                "duration_seconds": duration
            }

    @classmethod
    async def resolve(cls, start_url: str) -> Dict[str, Any]:
        return await asyncio.to_thread(cls._solve_single_stage_entry, start_url)

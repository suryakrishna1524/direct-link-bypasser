import re
import urllib.parse
import base64

COMMON_PARAMS = [
    'url', 'link', 'target', 'dest', 'destination', 'redirect', 'redir', 'r',
    'u', 'to', 'go', 'out', 'view', 'safelink_redirect', 'q', 'href'
]

class QueryDecoder:
    @staticmethod
    def is_valid_url(url: str) -> bool:
        return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', url, re.IGNORECASE))

    @classmethod
    def try_decode_base64(cls, text: str) -> str | None:
        try:
            # Fix padding if needed
            padded = text + '=' * (-len(text) % 4)
            decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            if cls.is_valid_url(decoded):
                return decoded
            # Try url-decoding after base64
            url_decoded = urllib.parse.unquote(decoded)
            if cls.is_valid_url(url_decoded):
                return url_decoded
        except Exception:
            pass
        return None

    @classmethod
    def extract_from_url(cls, url: str) -> str | None:
        try:
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            for param in COMMON_PARAMS:
                if param in query_params:
                    val = query_params[param][0]
                    # Direct URL in query param
                    if cls.is_valid_url(val):
                        return val
                    # URL encoded URL in query param
                    unquoted = urllib.parse.unquote(val)
                    if cls.is_valid_url(unquoted):
                        return unquoted
                    # Base64 encoded URL in query param
                    b64_res = cls.try_decode_base64(val)
                    if b64_res:
                        return b64_res
                        
            # Check entire query string or fragment for base64 or url
            if parsed.query:
                b64_res = cls.try_decode_base64(parsed.query)
                if b64_res:
                    return b64_res
            if parsed.fragment:
                if cls.is_valid_url(parsed.fragment):
                    return parsed.fragment
                b64_res = cls.try_decode_base64(parsed.fragment)
                if b64_res:
                    return b64_res
                    
        except Exception:
            pass
        return None

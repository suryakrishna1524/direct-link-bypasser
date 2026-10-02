import os
import time
import json
import sqlite3
import hashlib
import urllib.parse
import httpx
from typing import Dict, Any, Optional, List

CONFIRMED_DESTINATION_DOMAINS = [
    't.me', 'telegram.me', 'telegram.dog',
    'drive.google.com', 'docs.google.com',
    'mega.nz', 'mega.co.nz',
    'mediafire.com',
    'github.com', 'raw.githubusercontent.com', 'gist.github.com',
    'youtube.com', 'youtu.be',
    'dropbox.com',
    '1fichier.com',
    'pixeldrain.com',
    'send.cm',
    'racaty.net',
    'krakenfiles.com',
    'gofile.io',
    'terabox.com', 'teraboxapp.com', '1024tera.com',
    'workupload.com',
    'zippyshare.com',
    'wetransfer.com',
    'solidfiles.com',
    'bayfiles.com',
    'anonfiles.com',
    'streamtape.com',
    'doodstream.com', 'dood.to',
    'vimeo.com',
    'archive.org',
    'sourceforge.net',
    'gitlab.com',
    'bitbucket.org'
]

CONFIRMED_FILE_EXTENSIONS = [
    '.zip', '.rar', '.7z', '.tar', '.gz', '.iso', '.bin', '.exe', '.msi', '.apk', '.dmg',
    '.mp4', '.mkv', '.avi', '.mov', '.mp3', '.flac', '.wav',
    '.pdf', '.epub', '.mobi', '.doc', '.docx'
]

KNOWN_SHORTENER_HINTS = [
    'short', 'link', 'safe', 'url', 'drop', 'fly', 'earn', 'shrink',
    'tiny', 'bitly', 'wpsafelink', 'adlinkfly', 'cut'
]

class BypassDatabase:
    """
    High-speed dual-tier community cache database for bypassed links.
    
    Tier 1: Global Cloud KV (Upstash Redis / Vercel KV REST API via env vars)
    Tier 2: In-Memory Fast LRU Cache + Local/Vercel SQLite (/tmp/bypass_cache.db)
    
    Smart Filtering:
    - Auto-caches ONLY when destination link is confirmed expected media (Telegram, Drive, Mega, Mediafire, direct downloads).
    - Requires explicit user approval/submission for intermediate or unrecognized links.
    - Allows users to force-refresh or submit corrected direct links.
    """
    _memory_cache: Dict[str, Dict[str, Any]] = {}
    _db_path: str = ""
    _upstash_url: str = ""
    _upstash_token: str = ""

    @classmethod
    def _init_db(cls):
        if cls._db_path:
            return

        # Determine best SQLite path (use /tmp on Vercel / Linux, or local dir on Windows)
        if os.name != 'nt' and os.path.exists('/tmp'):
            cls._db_path = '/tmp/bypass_cache.db'
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cls._db_path = os.path.join(base_dir, 'bypass_cache.db')

        # Check cloud Upstash / Vercel KV env vars
        cls._upstash_url = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL") or ""
        cls._upstash_token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""

        try:
            with sqlite3.connect(cls._db_path, timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bypass_cache (
                        url_hash TEXT PRIMARY KEY,
                        original_url TEXT NOT NULL,
                        final_url TEXT NOT NULL,
                        intermediate INTEGER DEFAULT 0,
                        verified INTEGER DEFAULT 0,
                        hops_json TEXT,
                        method TEXT,
                        time_saved INTEGER DEFAULT 60,
                        hits INTEGER DEFAULT 1,
                        created_at REAL,
                        updated_at REAL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON bypass_cache(created_at)")
                
                # Dynamic column migration for existing tables
                cursor.execute("PRAGMA table_info(bypass_cache)")
                cols = [row[1] for row in cursor.fetchall()]
                if 'verified' not in cols:
                    cursor.execute("ALTER TABLE bypass_cache ADD COLUMN verified INTEGER DEFAULT 0")
                if 'intermediate' not in cols:
                    cursor.execute("ALTER TABLE bypass_cache ADD COLUMN intermediate INTEGER DEFAULT 0")
                if 'time_saved' not in cols:
                    cursor.execute("ALTER TABLE bypass_cache ADD COLUMN time_saved INTEGER DEFAULT 60")
                if 'hits' not in cols:
                    cursor.execute("ALTER TABLE bypass_cache ADD COLUMN hits INTEGER DEFAULT 1")
                conn.commit()
        except Exception as e:
            print("SQLite init warning:", e)

    @classmethod
    def is_confirmed_destination(cls, url: str) -> bool:
        if not url:
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()

            # 1. Check known media/file hosts
            if any(d in domain for d in CONFIRMED_DESTINATION_DOMAINS):
                return True

            # 2. Check direct file downloads
            if any(path.endswith(ext) for ext in CONFIRMED_FILE_EXTENSIONS):
                return True

            # 3. Reject known intermediate shorteners
            if any(h in domain for h in KNOWN_SHORTENER_HINTS):
                return False

            return False
        except Exception:
            return False

    @staticmethod
    def normalize_url(url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        try:
            parsed = urllib.parse.urlparse(url)
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path.rstrip('/') or '/'
            query = parsed.query
            normalized = urllib.parse.urlunparse((scheme, netloc, path, parsed.params, query, ''))
            return normalized
        except Exception:
            return url

    @classmethod
    def get_hash(cls, url: str) -> str:
        norm = cls.normalize_url(url)
        return hashlib.sha256(norm.encode('utf-8')).hexdigest()

    @classmethod
    async def get_cached_bypass(cls, raw_url: str) -> Optional[Dict[str, Any]]:
        cls._init_db()
        norm_url = cls.normalize_url(raw_url)
        url_hash = cls.get_hash(norm_url)

        # 1. Tier 1: In-Memory Fast Cache (0.0001s)
        if url_hash in cls._memory_cache:
            entry = cls._memory_cache[url_hash]
            entry['hits'] = entry.get('hits', 1) + 1
            return dict(entry)

        # 2. Tier 2: Cloud KV / Upstash Redis (if configured in Vercel)
        if cls._upstash_url and cls._upstash_token:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(
                        f"{cls._upstash_url.rstrip('/')}/get/bypass_{url_hash}",
                        headers={"Authorization": f"Bearer {cls._upstash_token}"}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        result_str = data.get("result")
                        if result_str:
                            cached_item = json.loads(result_str)
                            cls._memory_cache[url_hash] = cached_item
                            return cached_item
            except Exception:
                pass

        # 3. Tier 3: SQLite Cache
        try:
            with sqlite3.connect(cls._db_path, timeout=3.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT final_url, intermediate, verified, hops_json, method, time_saved, hits, created_at
                    FROM bypass_cache WHERE url_hash = ?
                """, (url_hash,))
                row = cursor.fetchone()
                if row:
                    final_url, intermediate, verified, hops_json, method, time_saved, hits, created_at = row
                    hops = []
                    try:
                        hops = json.loads(hops_json) if hops_json else []
                    except Exception:
                        hops = []

                    cached_item = {
                        "original_url": norm_url,
                        "final_url": final_url,
                        "intermediate": bool(intermediate),
                        "verified": bool(verified),
                        "hops": hops,
                        "method": method or "Community Cloud Cache",
                        "time_saved_seconds": time_saved or 60,
                        "hits": (hits or 1) + 1,
                        "cached": True
                    }

                    # Increment hit count
                    cursor.execute("UPDATE bypass_cache SET hits = hits + 1, updated_at = ? WHERE url_hash = ?", (time.time(), url_hash))
                    conn.commit()

                    # Save into memory
                    cls._memory_cache[url_hash] = cached_item
                    return cached_item
        except Exception as e:
            print("SQLite read warning:", e)

        return None

    @classmethod
    async def set_cached_bypass(
        cls,
        original_url: str,
        final_url: str,
        hops: List[Dict[str, Any]] = None,
        method: str = "Automated Bypass",
        intermediate: bool = False,
        time_saved: int = 60,
        user_verified: bool = False
    ) -> bool:
        # If user verified, mark as verified destination
        is_confirmed = user_verified or cls.is_confirmed_destination(final_url)

        cls._init_db()
        norm_url = cls.normalize_url(original_url)
        url_hash = cls.get_hash(norm_url)
        hops = hops or []
        hops_json = json.dumps(hops)
        now = time.time()

        cached_item = {
            "original_url": norm_url,
            "final_url": final_url,
            "intermediate": intermediate,
            "verified": is_confirmed,
            "hops": hops,
            "method": method,
            "time_saved_seconds": time_saved,
            "hits": 1,
            "cached": True,
            "created_at": now
        }

        # 1. Update In-Memory Cache
        cls._memory_cache[url_hash] = cached_item

        # 2. Update SQLite Cache
        try:
            with sqlite3.connect(cls._db_path, timeout=3.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO bypass_cache (url_hash, original_url, final_url, intermediate, verified, hops_json, method, time_saved, hits, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(url_hash) DO UPDATE SET
                        final_url = excluded.final_url,
                        intermediate = excluded.intermediate,
                        verified = excluded.verified,
                        hops_json = excluded.hops_json,
                        method = excluded.method,
                        time_saved = excluded.time_saved,
                        hits = bypass_cache.hits + 1,
                        updated_at = excluded.updated_at
                """, (url_hash, norm_url, final_url, int(intermediate), int(is_confirmed), hops_json, method, time_saved, now, now))
                conn.commit()
        except Exception as e:
            print("SQLite write warning:", e)

        # 3. Update Cloud KV / Upstash Redis (if configured)
        if cls._upstash_url and cls._upstash_token:
            try:
                payload = json.dumps(cached_item)
                async with httpx.AsyncClient(timeout=3.0) as client:
                    # Cache for 30 days (2,592,000 seconds)
                    await client.post(
                        f"{cls._upstash_url.rstrip('/')}/set/bypass_{url_hash}?ex=2592000",
                        headers={"Authorization": f"Bearer {cls._upstash_token}"},
                        content=payload
                    )
            except Exception:
                pass

        return True

    @classmethod
    async def delete_cached_bypass(cls, raw_url: str) -> bool:
        cls._init_db()
        norm_url = cls.normalize_url(raw_url)
        url_hash = cls.get_hash(norm_url)

        # Remove from memory
        cls._memory_cache.pop(url_hash, None)

        # Remove from SQLite
        try:
            with sqlite3.connect(cls._db_path, timeout=3.0) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM bypass_cache WHERE url_hash = ?", (url_hash,))
                conn.commit()
        except Exception:
            pass

        # Remove from Cloud KV
        if cls._upstash_url and cls._upstash_token:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    await client.post(
                        f"{cls._upstash_url.rstrip('/')}/del/bypass_{url_hash}",
                        headers={"Authorization": f"Bearer {cls._upstash_token}"}
                    )
            except Exception:
                pass

        return True

    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        cls._init_db()
        total_cached = len(cls._memory_cache)
        total_hits = 0
        try:
            with sqlite3.connect(cls._db_path, timeout=2.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), SUM(hits) FROM bypass_cache")
                row = cursor.fetchone()
                if row:
                    count, hits = row
                    total_cached = max(total_cached, count or 0)
                    total_hits = hits or 0
        except Exception:
            pass

        return {
            "total_cached_links": total_cached,
            "total_cache_hits": total_hits,
            "cloud_kv_enabled": bool(cls._upstash_url and cls._upstash_token)
        }

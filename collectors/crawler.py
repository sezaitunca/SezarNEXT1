"""
SEZARNEXT Collect — Crawler
===========================
Nazik (polite) tarayıcı: robots.txt'e uyar, hız sınırlar, içerik hash'i ile
değişiklik takibi yapar ve ham HTML'i data/raw altına arşivler.

Ağ kapalıysa hata vermez; toplanan kayıt sayısı 0 döner (offline demo uyumlu).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT = "SEZARNEXT-Crawler/1.0 (+research; participation-banking-intelligence)"
RAW_DIR = Path("data/raw")


@dataclass
class FetchResult:
    url: str
    status: int
    html: str = ""
    fetched_at: datetime = field(default_factory=datetime.now)
    content_hash: str = ""
    changed: bool = True
    error: str | None = None


class PoliteCrawler:
    def __init__(self, delay: float = 1.5, timeout: int = 15, raw_dir: Path = RAW_DIR) -> None:
        self.delay = delay
        self.timeout = timeout
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self._robots: dict[str, RobotFileParser] = {}
        self._hashes: dict[str, str] = self._load_hashes()

    # -- robots -------------------------------------------------------
    def allowed(self, url: str) -> bool:
        host = urlparse(url).netloc
        if host not in self._robots:
            rp = RobotFileParser()
            rp.set_url(f"{urlparse(url).scheme}://{host}/robots.txt")
            try:
                rp.read()
            except Exception:
                rp = None  # type: ignore
            self._robots[host] = rp
        rp = self._robots.get(host)
        if rp is None:
            return True
        try:
            return rp.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    # -- değişiklik takibi -------------------------------------------
    def _hash_path(self) -> Path:
        return self.raw_dir / "_hashes.json"

    def _load_hashes(self) -> dict[str, str]:
        p = self._hash_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_hashes(self) -> None:
        self._hash_path().write_text(
            json.dumps(self._hashes, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # -- fetch --------------------------------------------------------
    def fetch(self, url: str) -> FetchResult:
        if not self.allowed(url):
            return FetchResult(url=url, status=999, error="robots.txt tarafından engellendi")
        try:
            import requests

            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=self.timeout)
            html = resp.text
            h = hashlib.sha256(html.encode("utf-8", "ignore")).hexdigest()[:32]
            changed = self._hashes.get(url) != h
            self._hashes[url] = h
            res = FetchResult(url=url, status=resp.status_code, html=html,
                              content_hash=h, changed=changed)
            if changed and resp.status_code == 200:
                self._archive(res)
            time.sleep(self.delay)
            return res
        except Exception as exc:
            return FetchResult(url=url, status=0, error=str(exc))

    def _archive(self, res: FetchResult) -> None:
        name = hashlib.md5(res.url.encode()).hexdigest()[:16]
        day = res.fetched_at.strftime("%Y%m%d")
        out = self.raw_dir / day
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{name}.html").write_text(res.html, encoding="utf-8")
        (out / f"{name}.meta.json").write_text(
            json.dumps(
                {"url": res.url, "fetched_at": res.fetched_at.isoformat(),
                 "hash": res.content_hash, "status": res.status},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

    def crawl(self, urls: list[str]) -> list[FetchResult]:
        out = [self.fetch(u) for u in urls]
        self._save_hashes()
        return out

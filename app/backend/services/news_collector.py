"""News Collector: mengambil berita eksternal dari RSS.

Prinsip:
- hanya membaca feed RSS resmi (tidak scraping halaman),
- satu request per sumber per jadwal, dengan timeout,
- deduplikasi berdasarkan SHA-256 guid/URL item,
- kegagalan satu sumber hanya dicatat, tidak menghentikan Flask
  maupun sumber lain,
- berita baru berstatus PENDING sampai dimoderasi admin.
"""

import calendar
import hashlib
import html
import logging
import re
import threading
from datetime import datetime, timezone

import feedparser
import requests

from config import Config
from models import admin_model, news_model, region_model
from services import region_engine

logger = logging.getLogger(__name__)

_run_lock = threading.Lock()
TAG_RE = re.compile(r"<[^>]+>")


class CollectorBusy(RuntimeError):
    """Pengumpulan berita lain sedang berjalan."""


def collect_all(admin_id=None, ip_address=None):
    """Mengumpulkan berita dari semua sumber aktif.

    Aman dipanggil dari scheduler maupun dari endpoint admin. Tidak
    pernah melempar exception kecuali CollectorBusy.
    """
    if not _run_lock.acquire(blocking=False):
        raise CollectorBusy("Pengumpulan berita sedang berjalan.")
    summary = {"sources": 0, "fetched": 0, "inserted": 0, "errors": []}
    try:
        sources = news_model.list_sources(active_only=True)
        keywords = _keyword_index()
        for source in sources:
            summary["sources"] += 1
            try:
                fetched, inserted = _collect_source(source, keywords)
                summary["fetched"] += fetched
                summary["inserted"] += inserted
                news_model.mark_source_checked(source["id"])
            except Exception as exc:  # noqa: BLE001 - satu sumber gagal
                logger.warning("RSS %s gagal: %s", source["rss_url"], exc)
                summary["errors"].append(
                    {"source": source["name"], "error": str(exc)[:200]}
                )
                _safe_mark_error(source["id"], exc)
        admin_model.log_activity(
            admin_id, "IMPORT_NEWS",
            f"{summary['inserted']} berita baru dari "
            f"{summary['sources']} sumber "
            f"({len(summary['errors'])} gagal)",
            entity_type="news", ip_address=ip_address,
        )
    except Exception as exc:  # noqa: BLE001 - scheduler tidak boleh mati
        logger.exception("News collector gagal: %s", exc)
        summary["errors"].append({"source": "*", "error": str(exc)[:200]})
    finally:
        _run_lock.release()
    return summary


def scheduled_job():
    try:
        result = collect_all()
        logger.info("News collector: %s", result)
    except CollectorBusy:
        logger.info("News collector dilewati: proses lain masih berjalan.")


def _safe_mark_error(source_id, exc):
    try:
        news_model.mark_source_checked(source_id, error=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Tidak dapat menyimpan status sumber %s", source_id)


def _collect_source(source, keywords):
    response = requests.get(
        source["rss_url"],
        timeout=Config.NEWS_REQUEST_TIMEOUT,
        headers={"User-Agent": Config.NEWS_USER_AGENT},
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Feed tidak valid: {feed.bozo_exception}")

    entries = feed.entries[: Config.NEWS_MAX_ITEMS_PER_SOURCE]
    inserted = 0
    for entry in entries:
        item = _parse_entry(entry, source, keywords)
        if item and news_model.insert_news_if_new(item):
            inserted += 1
    return len(entries), inserted


def _parse_entry(entry, source, keywords):
    link = (entry.get("link") or "").strip()
    title = _clean(entry.get("title"))
    if not link.startswith(("http://", "https://")) or not title:
        return None
    identifier = entry.get("id") or entry.get("guid") or link
    summary = _clean(entry.get("summary") or entry.get("description"))

    region_id, method, matched = _detect_region(
        title, summary, source.get("region_id"), keywords
    )
    return {
        "source_id": source["id"],
        "external_id": hashlib.sha256(identifier.encode("utf-8")).hexdigest(),
        "title": title[:500],
        "summary": summary[:2000] or None,
        "source_url": link[:1000],
        "image_url": _image(entry),
        "author": _clean(entry.get("author"))[:150] or None,
        "published_at": _published(entry),
        "category_id": source.get("category_id"),
        "region_id": region_id,
        "relevance_method": method,
        "keywords": ", ".join(matched)[:500] or None,
    }


def _clean(text):
    if not text:
        return ""
    text = html.unescape(TAG_RE.sub(" ", str(text)))
    return " ".join(text.split())


def _image(entry):
    candidates = []
    for key in ("media_content", "media_thumbnail"):
        candidates += [m.get("url") for m in entry.get(key, []) or []]
    for enclosure in entry.get("enclosures", []) or []:
        if (enclosure.get("type") or "").startswith("image/"):
            candidates.append(enclosure.get("href"))
    for url in candidates:
        if url and url.startswith(("http://", "https://")):
            return url[:1000]
    return None


def _published(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    timestamp = calendar.timegm(parsed)
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(
        tzinfo=None
    )


# ----------------------------------------------------- region analysis

def _keyword_index():
    index = []
    for row in region_model.list_all_keywords():
        pattern = re.compile(
            r"(?<!\w)" + re.escape(row["keyword"]) + r"(?!\w)", re.IGNORECASE
        )
        index.append((row["region_id"], row["keyword"], pattern))
    return index


def _detect_region(title, summary, metadata_region_id, keywords):
    """Memperkirakan wilayah berita secara konservatif.

    Keyword dianggap bukti hanya jika muncul di judul, atau muncul
    minimal dua kali di ringkasan. Jika tidak ada bukti cukup, wilayah
    dibiarkan kosong (atau memakai metadata sumber).
    """
    candidates, matched = {}, []
    for region_id, keyword, pattern in keywords:
        in_title = bool(pattern.search(title))
        in_summary = len(pattern.findall(summary))
        if in_title or in_summary >= 2:
            candidates[region_id] = candidates.get(region_id, 0) + 1
            matched.append(keyword)

    keyword_region = None
    if candidates:
        keyword_region = max(
            candidates, key=lambda rid: (region_engine.depth(rid),
                                         candidates[rid])
        )

    if keyword_region and metadata_region_id:
        if metadata_region_id in region_engine.ancestor_ids(keyword_region):
            return keyword_region, "KEYWORD_AND_METADATA", matched
        return keyword_region, "KEYWORD", matched
    if keyword_region:
        return keyword_region, "KEYWORD", matched
    if metadata_region_id:
        return metadata_region_id, "METADATA", matched
    return None, None, matched

"""Feed Engine: menggabungkan Information, Event, dan News.

Setiap sumber di-query terpisah (sudah terurut), lalu digabung dan
diurutkan ulang di Python. Untuk halaman ke-N cukup mengambil
N x per_page baris teratas dari setiap sumber.
"""

from datetime import datetime

from models import event_model, information_model, news_model
from services import region_engine

FEED_TYPES = ("information", "event", "news")
MAX_WINDOW = 600


def _information_item(row):
    return {
        "type": "information",
        "id": row["id"],
        "title": row["title"],
        "description": row["summary"] or _excerpt(row["content"]),
        "category": row["category_name"],
        "category_id": row["category_id"],
        "region": row["region_name"],
        "region_id": row["region_id"],
        "priority": row["priority"],
        "image": row["image"],
        "created_at": row["sort_at"],
        "sort_at": row["sort_at"],
    }


def _event_item(row):
    return {
        "type": "event",
        "id": row["id"],
        "title": row["title"],
        "description": _excerpt(row["description"]),
        "category": row["category_name"],
        "category_id": row["category_id"],
        "region": row["region_name"],
        "region_id": row["region_id"],
        "location": row["location_name"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "created_at": row["created_at"],
        "sort_at": row["sort_at"],
    }


def _news_item(row):
    return {
        "type": "news",
        "id": row["id"],
        "title": row["title"],
        "description": _excerpt(row["summary"]),
        "category": row["category_name"],
        "category_id": row["category_id"],
        "region": row["region_name"],
        "region_id": row["region_id"],
        "relevance_method": row["relevance_method"],
        "source": row["source_name"],
        "url": row["source_url"],
        "image": row["image_url"],
        "published_at": row["published_at"],
        "created_at": row["sort_at"],
        "sort_at": row["sort_at"],
    }


def _excerpt(text, length=220):
    if not text:
        return ""
    text = " ".join(text.split())
    return text if len(text) <= length else text[: length - 1] + "…"


SOURCES = {
    "information": (information_model.list_information, _information_item),
    "event": (event_model.list_events, _event_item),
    "news": (news_model.list_news, _news_item),
}


def get_feed(filters, page=1, per_page=12):
    """filters: region_id, category_id, types, q, date_from, date_to, sort."""
    types = [t for t in filters.get("types") or FEED_TYPES
             if t in FEED_TYPES]
    query = {
        "public": True,
        "category_id": filters.get("category_id"),
        "q": filters.get("q"),
        "date_from": filters.get("date_from"),
        "date_to": filters.get("date_to"),
        "sort": filters.get("sort", "newest"),
    }
    region = None
    if filters.get("region_id"):
        chain = region_engine.hierarchy(filters["region_id"])
        if chain:
            region = chain[-1]
            query["region_ids"] = region_engine.related_ids(region["id"])
        else:
            query["region_ids"] = [filters["region_id"]]

    window = min(page * per_page, MAX_WINDOW)
    items, total = [], 0
    for feed_type in types:
        list_fn, to_item = SOURCES[feed_type]
        result = list_fn(query, page=1, per_page=window)
        total += result["total"]
        items.extend(to_item(row) for row in result["items"])

    sort = query["sort"]
    if sort == "title":
        items.sort(key=lambda item: item["title"].lower())
    else:
        items.sort(key=lambda item: item["sort_at"] or datetime.min,
                   reverse=sort != "oldest")

    start = (page - 1) * per_page
    page_items = items[start:start + per_page]
    for item in page_items:
        item.pop("sort_at", None)
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page else 0,
        "region": region,
        "types": types,
    }

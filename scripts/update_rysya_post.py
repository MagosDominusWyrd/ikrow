#!/usr/bin/env python3

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


AUTHOR_HANDLE = "ikrow.space"
AUTHOR_DID = "did:plc:smisl44l2n5wmgl6ecqnapr4"
TARGET_TAG = "山猫リシャ"

FEED_LIMIT = 100
OUTPUT_FILE = Path("data/rysya-latest.json")

AUTHOR_FEED_URL = (
    "https://public.api.bsky.app/xrpc/"
    "app.bsky.feed.getAuthorFeed"
)

OEMBED_URL = "https://embed.bsky.app/oembed"


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ikrow.space Bluesky updater/1.0"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def extract_tags(record: dict) -> set[str]:
    tags: set[str] = set()

    for facet in record.get("facets", []):
        for feature in facet.get("features", []):
            if feature.get("$type") == "app.bsky.richtext.facet#tag":
                tag = feature.get("tag")

                if tag:
                    tags.add(tag)

    return tags


def find_latest_rysya_post(feed: list[dict]) -> dict:
    for item in feed:
        post = item.get("post", {})
        author = post.get("author", {})
        record = post.get("record", {})

        if author.get("did") != AUTHOR_DID:
            continue

        if TARGET_TAG not in extract_tags(record):
            continue

        return post

    raise RuntimeError(
        f"Не найден пост автора {AUTHOR_HANDLE} "
        f"с хэштегом #{TARGET_TAG} среди последних {FEED_LIMIT} записей."
    )


def make_post_url(post_uri: str) -> str:
    post_key = post_uri.rsplit("/", 1)[-1]

    if not post_key:
        raise RuntimeError(f"Не удалось определить идентификатор поста: {post_uri}")

    return f"https://bsky.app/profile/{AUTHOR_HANDLE}/post/{post_key}"


def main() -> int:
    query = urllib.parse.urlencode(
        {
            "actor": AUTHOR_HANDLE,
            "filter": "posts_no_replies",
            "limit": FEED_LIMIT,
        }
    )

    feed_data = fetch_json(f"{AUTHOR_FEED_URL}?{query}")
    post = find_latest_rysya_post(feed_data.get("feed", []))

    post_uri = post.get("uri", "")
    post_url = make_post_url(post_uri)

    oembed_query = urllib.parse.urlencode(
        {
            "url": post_url,
            "format": "json",
            "maxwidth": 600,
        }
    )

    oembed_data = fetch_json(f"{OEMBED_URL}?{oembed_query}")

    output = {
        "uri": post_uri,
        "url": post_url,
        "createdAt": post.get("record", {}).get("createdAt", ""),
        "html": oembed_data.get("html", ""),
    }

    if not output["html"]:
        raise RuntimeError("Bluesky oEmbed не вернул HTML-код публикации.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    new_content = json.dumps(
        output,
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    old_content = (
        OUTPUT_FILE.read_text(encoding="utf-8")
        if OUTPUT_FILE.exists()
        else None
    )

    if old_content == new_content:
        print("Последний пост Рыси не изменился.")
        return 0

    OUTPUT_FILE.write_text(new_content, encoding="utf-8")

    print(f"Обновлен пост Рыси: {post_url}")
    print(f"Файл сохранен: {OUTPUT_FILE}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        raise SystemExit(1)
import json
import os
import sys
import requests
import feedparser
from datetime import datetime, timezone

RSS_URL = "https://services.lesechos.fr/rss/les-echos-economie.xml"
OUTPUT_DIR = "output"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://www.lesechos.fr/",
}


def fetch_feed():
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        r = session.get(RSS_URL, timeout=30, allow_redirects=True)
        r.raise_for_status()
        return r.content
    except requests.RequestException as e:
        print(f"Erreur reseau : {e}", file=sys.stderr)
        sys.exit(1)


def parse_entry(entry):
    media_list = entry.get("media_content") or []
    media_item = media_list[0] if media_list else {}

    tags = entry.get("tags") or []
    category = tags[0].get("term", "") if tags else ""

    return {
        "id": entry.get("id", ""),
        "title": (entry.get("title") or "").strip(),
        "description": (entry.get("summary") or "").strip(),
        "link": entry.get("link", ""),
        "category": category,
        "pub_date": entry.get("published", ""),
        "image_url": media_item.get("url", ""),
        "image_width": media_item.get("width", ""),
        "image_height": media_item.get("height", ""),
        "image_description": entry.get("media_description", ""),
        "image_credit": entry.get("media_credit", ""),
    }


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_markdown(data, path):
    lines = [
        f"# {data['source']}",
        "",
        f"> Derniere mise a jour : `{data['last_fetched']}`  ",
        f"> Source : [{data['source_url']}]({data['source_url']})",
        f"> {data['total_items']} articles indexes",
        "",
        "---",
        "",
    ]

    for a in data["articles"]:
        lines += [
            f"### [{a['title']}]({a['link']})",
            "",
            f"`{a['pub_date']}` | *{a['category']}*",
            "",
        ]
        if a["image_url"]:
            lines.append(f"![{a['title']}]({a['image_url']})")
            lines.append("")
        lines += [
            a["description"],
            "",
            "---",
            "",
        ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    content = fetch_feed()
    feed = feedparser.parse(content)

    articles = [parse_entry(e) for e in feed.entries]

    output = {
        "source": feed.feed.get("title", "Les Echos - Economie"),
        "source_url": feed.feed.get(
            "link", "https://www.lesechos.fr/economie-france"
        ),
        "language": feed.feed.get("language", "fr-FR"),
        "copyright": feed.feed.get("rights", "Les Echos 2026"),
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "last_build": feed.feed.get("updated", ""),
        "total_items": len(articles),
        "articles": articles,
    }

    save_json(output, os.path.join(OUTPUT_DIR, "feed.json"))
    save_markdown(output, os.path.join(OUTPUT_DIR, "feed.md"))

    print(f"OK {len(articles)} articles | build: {output['last_build']}")


if __name__ == "__main__":
    main()

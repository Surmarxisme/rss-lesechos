import json
import os
import sys
import feedparser
from datetime import datetime, timezone

RSS_URL = "https://services.lesechos.fr/rss/les-echos-economie.xml"
OUTPUT_DIR = "output"

# feedparser envoie ses propres headers HTTP qui passent mieux les protections
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def fetch_and_parse():
    feed = feedparser.parse(
        RSS_URL,
        request_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Referer": "https://www.lesechos.fr/",
            "Cache-Control": "no-cache",
        }
    )
    if feed.bozo and not feed.entries:
        exc = feed.get("bozo_exception", "unknown error")
        print(f"Erreur RSS : {exc}", file=sys.stderr)
        # Si 403 ou erreur reseau, on sort avec code 1
        if hasattr(exc, 'code') and exc.code in (403, 401, 429):
            print(f"HTTP {exc.code} - le serveur bloque les requetes automatisees", file=sys.stderr)
            sys.exit(1)
    return feed


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
    feed = fetch_and_parse()

    articles = [parse_entry(e) for e in feed.entries]

    if not articles:
        print("Aucun article recupere - le flux est peut-etre vide ou inaccessible", file=sys.stderr)
        sys.exit(1)

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

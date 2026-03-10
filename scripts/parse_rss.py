import json
import os
import sys
import feedparser
from datetime import datetime, timezone

# Google News RSS - Economie France (pas de blocage IP AWS)
# Filtre sur les sources Les Echos via Google News
RSS_URL = "https://news.google.com/rss/search?q=site:lesechos.fr+economie&hl=fr&gl=FR&ceid=FR:fr"
OUTPUT_DIR = "output"

# User-Agent standard
feedparser.USER_AGENT = "Mozilla/5.0 (compatible; FeedFetcher/1.0)"


def fetch_and_parse():
    feed = feedparser.parse(RSS_URL)
    if feed.bozo and not feed.entries:
        exc = feed.get("bozo_exception", "erreur inconnue")
        print(f"Erreur RSS : {exc}", file=sys.stderr)
        sys.exit(1)
    return feed


def parse_entry(entry):
    return {
        "id": entry.get("id", ""),
        "title": (entry.get("title") or "").strip(),
        "description": (entry.get("summary") or "").strip(),
        "link": entry.get("link", ""),
        "category": "",
        "pub_date": entry.get("published", ""),
        "image_url": "",
        "image_width": "",
        "image_height": "",
        "image_description": "",
        "image_credit": "",
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
            f"`{a['pub_date']}`",
            "",
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
        print("Aucun article recupere", file=sys.stderr)
        sys.exit(1)

    output = {
        "source": "Les Echos - Economie (via Google News)",
        "source_url": "https://www.lesechos.fr/economie-france",
        "language": "fr-FR",
        "copyright": "Les Echos",
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

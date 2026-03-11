import json, os, sys, requests, feedparser
from datetime import datetime, timezone

RSS_URL = "https://services.lesechos.fr/rss/les-echos-economie.xml"
OUTPUT_DIR = "output"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RSSFetcher/2.0; +https://github.com)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def fetch_feed():
    try:
        r = requests.get(RSS_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.content

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            print(
                "⚠️ Accès refusé (403) par le serveur Les Echos. "
                "Probable blocage des IP GitHub Actions. Aucune mise à jour effectuée."
            )
            sys.exit(0)

        print(f"❌ Erreur HTTP : {e}", file=sys.stderr)
        sys.exit(1)

    except requests.RequestException as e:
        print(f"❌ Erreur réseau : {e}", file=sys.stderr)
        sys.exit(1)


def parse_entry(entry):
    media = entry.get("media_content", [{}])
    media_item = media[0] if media else {}
    return {
        "id":                entry.get("id", ""),
        "title":             entry.get("title", "").strip(),
        "description":       entry.get("summary", "").strip(),
        "link":              entry.get("link", ""),
        "category":          entry.get("tags", [{}])[0].get("term", "") if entry.get("tags") else "",
        "pub_date":          entry.get("published", ""),
        "image_url":         media_item.get("url", ""),
        "image_width":       media_item.get("width", ""),
        "image_height":      media_item.get("height", ""),
        "image_description": entry.get("media_description", ""),
        "image_credit":      entry.get("media_credit", ""),
    }


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_markdown(data, path):
    lines = [
        f"# {data['source']}",
        "",
        f"> 🕐 Dernière mise à jour : `{data['last_fetched']}`  ",
        f"> 📡 [Voir sur lesechos.fr]({data['source_url']})  ",
        f"> 📰 **{data['total_items']} articles indexés**",
        "",
        "---",
        "",
    ]
    for a in data["articles"]:
        lines += [
            f"### [{a['title']}]({a['link']})",
            "",
            f"📅 `{a['pub_date']}` | 🏷️ *{a['category']}*",
            "",
        ]
        if a["image_url"]:
            lines += [f"![{a['title']}]({a['image_url']})", ""]
        lines += [a["description"], "", "---", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    content = fetch_feed()

    feed = feedparser.parse(content)
    articles = [parse_entry(e) for e in feed.entries]

    output = {
        "source":       feed.feed.get("title", "Les Echos - Economie"),
        "source_url":   feed.feed.get("link", "https://www.lesechos.fr/economie-france"),
        "language":     feed.feed.get("language", "fr-FR"),
        "copyright":    feed.feed.get("rights", "Les Echos 2026"),
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "last_build":   feed.feed.get("updated", ""),
        "total_items":  len(articles),
        "articles":     articles,
    }

    save_json(output, os.path.join(OUTPUT_DIR, "feed.json"))
    save_markdown(output, os.path.join(OUTPUT_DIR, "feed.md"))
    print(f"✅ {len(articles)} articles sauvegardés | build: {output['last_build']}")


if __name__ == "__main__":
    main()

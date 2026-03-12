import json, os, sys, requests, feedparser
from datetime import datetime, timezone

# Google News RSS - cible la rubrique economie-france de lesechos.fr
# La requete site:lesechos.fr/economie-france est deja le meilleur filtre disponible
RSS_URL = "https://news.google.com/rss/search?q=site:lesechos.fr/economie-france&hl=fr&gl=FR&ceid=FR:fr"
OUTPUT_DIR = "output"

# Domaines a exclure (sous-domaines non voulus)
EXCLUDE_DOMAINS = ["investir.lesechos.fr", "business.lesechos.fr"]

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
        print(f"Erreur HTTP : {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Erreur reseau : {e}", file=sys.stderr)
        sys.exit(1)


def should_exclude(entry):
    """Retourne True si l'article provient d'un sous-domaine exclu."""
    # On cherche dans le titre, le summary et la source
    text = " ".join([
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("source", {}).get("value", "") if entry.get("source") else "",
        entry.get("link", ""),
    ])
    return any(domain in text for domain in EXCLUDE_DOMAINS)


def parse_entry(entry):
    return {
        "id":          entry.get("id", ""),
        "title":       entry.get("title", "").strip(),
        "description": entry.get("summary", "").strip(),
        "link":        entry.get("link", ""),
        "source":      entry.get("source", {}).get("value", "Les Echos") if entry.get("source") else "Les Echos",
        "pub_date":    entry.get("published", ""),
    }


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_markdown(data, path):
    lines = [
        f"# {data['source']}",
        "",
        f"> Derniere mise a jour : `{data['last_fetched']}`",
        f"> {data['total_items']} articles - rubrique Economie France",
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
    content = fetch_feed()

    feed = feedparser.parse(content)
    total_raw = len(feed.entries)

    # Exclure seulement les sous-domaines indesirables
    filtered = [e for e in feed.entries if not should_exclude(e)]
    articles = [parse_entry(e) for e in filtered]
    total_kept = len(articles)

    print(f"Recuperes : {total_raw} | Gardes apres exclusions : {total_kept}")

    output = {
        "source":       "Les Echos - Economie France",
        "source_url":   "https://www.lesechos.fr/economie-france",
        "language":     "fr-FR",
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "last_build":   feed.feed.get("updated", ""),
        "total_items":  total_kept,
        "articles":     articles,
    }

    save_json(output, os.path.join(OUTPUT_DIR, "feed.json"))
    save_markdown(output, os.path.join(OUTPUT_DIR, "feed.md"))
    print(f"OK : {total_kept} articles sauvegardes")


if __name__ == "__main__":
    main()

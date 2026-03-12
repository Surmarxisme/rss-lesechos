import json, os, sys, requests, feedparser
from datetime import datetime, timezone

# Google News RSS - recherche uniquement sur lesechos.fr/economie-france
# On utilise inurl: pour cibler la rubrique exacte
RSS_URL = "https://news.google.com/rss/search?q=site:lesechos.fr/economie-france&hl=fr&gl=FR&ceid=FR:fr"
OUTPUT_DIR = "output"

# Filtre : on ne garde que les liens pointant vers lesechos.fr/economie-france
FILTER_URL = "lesechos.fr/economie-france"

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


def extract_real_link(entry):
    """Google News encapsule les vrais liens dans le champ summary ou link.
    On recupere le vrai lien lesechos depuis le champ 'link' ou le summary HTML."""
    import re
    # Tentative 1 : lien direct
    link = entry.get("link", "")
    if FILTER_URL in link:
        return link
    # Tentative 2 : extraire depuis le HTML du summary
    summary = entry.get("summary", "")
    match = re.search(r'href="(https://www\.lesechos\.fr/economie-france[^"]+)"', summary)
    if match:
        return match.group(1)
    return link


def parse_entry(entry):
    real_link = extract_real_link(entry)
    return {
        "id":          entry.get("id", ""),
        "title":       entry.get("title", "").strip(),
        "description": entry.get("summary", "").strip(),
        "link":        real_link,
        "source":      entry.get("source", {}).get("value", "Les Echos") if entry.get("source") else "Les Echos",
        "pub_date":    entry.get("published", ""),
    }


def is_economie_france(entry):
    """Ne garde que les articles dont le lien pointe vers lesechos.fr/economie-france."""
    link = extract_real_link(entry)
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    # Filtre sur le lien OU sur la presence de /economie-france dans le contenu
    return FILTER_URL in link or FILTER_URL in summary


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_markdown(data, path):
    lines = [
        f"# {data['source']}",
        "",
        f"> Derniere mise a jour : `{data['last_fetched']}`",
        f"> {data['total_items']} articles - rubrique Economie France uniquement",
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

    # Filtrage strict : uniquement lesechos.fr/economie-france
    filtered_entries = [e for e in feed.entries if is_economie_france(e)]
    articles = [parse_entry(e) for e in filtered_entries]

    total_raw = len(feed.entries)
    total_kept = len(articles)
    print(f"Recuperes : {total_raw} | Filtres (economie-france uniquement) : {total_kept}")

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

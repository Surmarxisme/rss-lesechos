import json, os, sys, re, requests, feedparser
from datetime import datetime, timezone

# Google News RSS cible site:lesechos.fr/economie-france
# Les liens Google News sont des redirections - on filtre sur le titre/source
RSS_URL = "https://news.google.com/rss/search?q=site:lesechos.fr/economie-france&hl=fr&gl=FR&ceid=FR:fr"
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
        print(f"Erreur HTTP : {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Erreur reseau : {e}", file=sys.stderr)
        sys.exit(1)


def extract_real_link(entry):
    """Extrait le vrai lien lesechos depuis le summary HTML de Google News."""
    summary = entry.get("summary", "")
    # Google News met le vrai lien dans un <a href="..."> dans le summary
    match = re.search(r'href="(https://(?:www\.)?lesechos\.fr/[^"]+)"', summary)
    if match:
        return match.group(1)
    # Fallback : lien Google News direct
    return entry.get("link", "")


def is_economie_france(entry):
    """Filtre : accepte uniquement les articles de lesechos.fr/economie-france.
    On filtre sur le vrai lien extrait du summary."""
    real_link = extract_real_link(entry)
    # Accepte si le vrai lien contient /economie-france
    if "lesechos.fr/economie-france" in real_link:
        return True
    # Fallback : si pas de lien direct trouve, on accepte quand meme
    # (Google News cible deja la bonne rubrique via la requete)
    fallback_link = entry.get("link", "")
    if "news.google.com" in fallback_link:
        # On ne peut pas verifier - on accepte par defaut
        # mais on rejette si un autre domaine lesechos est detecte
        summary = entry.get("summary", "")
        if "investir.lesechos.fr" in summary or "business.lesechos.fr" in summary:
            return False
        return True
    return False


def parse_entry(entry):
    real_link = extract_real_link(entry)
    return {
        "id":          entry.get("id", ""),
        "title":       entry.get("title", "").strip(),
        "description": entry.get("summary", "").strip(),
        "link":        real_link if real_link else entry.get("link", ""),
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
    total_raw = len(feed.entries)

    filtered = [e for e in feed.entries if is_economie_france(e)]
    articles = [parse_entry(e) for e in filtered]
    total_kept = len(articles)

    print(f"Recuperes : {total_raw} | Gardes (economie-france) : {total_kept}")

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

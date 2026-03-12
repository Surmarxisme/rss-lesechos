import json, os, sys, requests, feedparser
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Google News RSS - rubrique economie-france de lesechos.fr
RSS_URL = "https://news.google.com/rss/search?q=site:lesechos.fr/economie-france&hl=fr&gl=FR&ceid=FR:fr"
OUTPUT_DIR = "output"

# Ne garder que les articles des 30 derniers jours
# (comportement d'un vrai flux RSS)
MAX_AGE_DAYS = 30

# Sous-domaines a exclure
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


def parse_pub_date(entry):
    """Parse la date de publication, retourne None si invalide."""
    pub = entry.get("published", "")
    if not pub:
        return None
    try:
        return parsedate_to_datetime(pub).astimezone(timezone.utc)
    except Exception:
        return None


def is_recent(entry):
    """Retourne True si l'article a moins de MAX_AGE_DAYS jours."""
    pub_date = parse_pub_date(entry)
    if pub_date is None:
        # Si pas de date, on garde l'article par defaut
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    return pub_date >= cutoff


def should_exclude(entry):
    """Retourne True si l'article provient d'un sous-domaine exclu."""
    text = " ".join([
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("source", {}).get("value", "") if entry.get("source") else "",
        entry.get("link", ""),
    ])
    return any(domain in text for domain in EXCLUDE_DOMAINS)


def parse_entry(entry):
    pub_date = parse_pub_date(entry)
    return {
        "id":          entry.get("id", ""),
        "title":       entry.get("title", "").strip(),
        "description": entry.get("summary", "").strip(),
        "link":        entry.get("link", ""),
        "source":      entry.get("source", {}).get("value", "Les Echos") if entry.get("source") else "Les Echos",
        "pub_date":    entry.get("published", ""),
        "pub_date_iso": pub_date.isoformat() if pub_date else "",
    }


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_markdown(data, path):
    lines = [
        f"# {data['source']}",
        "",
        f"> Derniere mise a jour : `{data['last_fetched']}`",
        f"> {data['total_items']} articles recents (30 derniers jours)",
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

    # Filtre 1 : exclure sous-domaines indesirables
    # Filtre 2 : ne garder que les articles des 30 derniers jours
    filtered = [
        e for e in feed.entries
        if not should_exclude(e) and is_recent(e)
    ]
    articles = [parse_entry(e) for e in filtered]
    total_kept = len(articles)

    cutoff_str = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%d")
    print(f"Recuperes : {total_raw} | Apres filtre (< {MAX_AGE_DAYS}j, depuis {cutoff_str}) : {total_kept}")

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

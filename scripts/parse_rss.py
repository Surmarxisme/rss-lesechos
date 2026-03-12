import json, os, sys, requests, feedparser
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Google News RSS - rubrique economie-france de lesechos.fr
RSS_URL = "https://news.google.com/rss/search?q=site:lesechos.fr/economie-france&hl=fr&gl=FR&ceid=FR:fr"
OUTPUT_DIR = "output"
SEEN_IDS_FILE = os.path.join(OUTPUT_DIR, "seen_ids.json")

# Ne garder que les articles des 30 derniers jours
MAX_AGE_DAYS = 30

# Sous-domaines a exclure
EXCLUDE_DOMAINS = ["investir.lesechos.fr", "business.lesechos.fr"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RSSFetcher/2.0; +https://github.com)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

def load_seen_ids():
    """Charge les IDs deja vus depuis le fichier de persistance."""
    if os.path.exists(SEEN_IDS_FILE):
        try:
            with open(SEEN_IDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("ids", []))
        except Exception:
            pass
    return set()

def save_seen_ids(seen_ids):
    """Sauvegarde les IDs vus dans le fichier de persistance."""
    # On garde les IDs des 60 derniers jours max pour eviter un fichier trop grand
    with open(SEEN_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": list(seen_ids), "updated": datetime.now(timezone.utc).isoformat()}, f, ensure_ascii=False, indent=2)

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
        "id": entry.get("id", ""),
        "title": entry.get("title", "").strip(),
        "description": entry.get("summary", "").strip(),
        "link": entry.get("link", ""),
        "source": entry.get("source", {}).get("value", "Les Echos") if entry.get("source") else "Les Echos",
        "pub_date": entry.get("published", ""),
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
        f"> {data['total_items']} nouveaux articles (non deja vus, 30 derniers jours)",
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

    # Charger les IDs deja vus
    seen_ids = load_seen_ids()
    print(f"IDs deja vus : {len(seen_ids)}")

    content = fetch_feed()
    feed = feedparser.parse(content)
    total_raw = len(feed.entries)

    # Filtre 1 : exclure sous-domaines indesirables
    # Filtre 2 : ne garder que les articles des 30 derniers jours
    # Filtre 3 : exclure les articles deja vus
    new_entries = []
    for e in feed.entries:
        if should_exclude(e):
            continue
        if not is_recent(e):
            continue
        entry_id = e.get("id", "")
        if entry_id and entry_id in seen_ids:
            continue
        new_entries.append(e)

    articles = [parse_entry(e) for e in new_entries]
    total_new = len(articles)

    cutoff_str = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%d")
    print(f"Recuperes : {total_raw} | Nouveaux (non vus, < {MAX_AGE_DAYS}j) : {total_new}")

    # Mettre a jour les IDs vus avec les nouveaux articles
    for e in feed.entries:
        entry_id = e.get("id", "")
        if entry_id:
            seen_ids.add(entry_id)

    save_seen_ids(seen_ids)

    # On charge le feed existant et on PREPEND les nouveaux articles
    feed_path = os.path.join(OUTPUT_DIR, "feed.json")
    existing_articles = []
    if os.path.exists(feed_path):
        try:
            with open(feed_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                existing_articles = existing.get("articles", [])
        except Exception:
            pass

    # Fusion : nouveaux en premier, puis anciens (en evitant les doublons par id)
    existing_ids = {a["id"] for a in existing_articles}
    merged = articles + [a for a in existing_articles if a["id"] not in {a["id"] for a in articles}]

    # On ne garde que les articles des 30 derniers jours dans le feed final
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    def is_recent_article(a):
        iso = a.get("pub_date_iso", "")
        if not iso:
            return True
        try:
            return datetime.fromisoformat(iso) >= cutoff_dt
        except Exception:
            return True

    merged = [a for a in merged if is_recent_article(a)]

    output = {
        "source": "Les Echos - Economie France",
        "source_url": "https://www.lesechos.fr/economie-france",
        "language": "fr-FR",
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "last_build": feed.feed.get("updated", ""),
        "total_items": len(merged),
        "new_items_this_run": total_new,
        "articles": merged,
    }

    save_json(output, feed_path)
    save_markdown(output, os.path.join(OUTPUT_DIR, "feed.md"))
    print(f"OK : {total_new} nouveaux articles ajoutes, {len(merged)} articles au total dans le feed")

if __name__ == "__main__":
    main()

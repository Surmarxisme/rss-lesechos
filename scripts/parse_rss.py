import json
import os
import sys
import feedparser
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

OUTPUT_DIR = "output"

# Deux flux Google News cibles sur les rubriques exactes de Les Echos
RSS_FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=site:lesechos.fr/economie-france&hl=fr&gl=FR&ceid=FR:fr",
        "section": "economie-france",
    },
    {
        "url": "https://news.google.com/rss/search?q=site:lesechos.fr/idees-debats&hl=fr&gl=FR&ceid=FR:fr",
        "section": "idees-debats",
    },
]

# Seuls les liens pointant vers ces chemins sont gardes
ALLOWED_PATHS = ("/economie-france", "/idees-debats")

feedparser.USER_AGENT = "Mozilla/5.0 (compatible; FeedFetcher/1.0)"


def fetch_section(feed_cfg):
    feed = feedparser.parse(feed_cfg["url"])
    if feed.bozo and not feed.entries:
        exc = feed.get("bozo_exception", "erreur inconnue")
        print(f"Avertissement {feed_cfg['section']} : {exc}", file=sys.stderr)
        return []
    return feed.entries


def parse_entry(entry, section):
    media_list = entry.get("media_content") or []
    media_item = media_list[0] if media_list else {}
    tags = entry.get("tags") or []
    category = tags[0].get("term", section) if tags else section
    return {
        "id":                entry.get("id", ""),
        "title":             (entry.get("title") or "").strip(),
        "description":       (entry.get("summary") or "").strip(),
        "link":              entry.get("link", ""),
        "section":           section,
        "category":          category,
        "pub_date":          entry.get("published", ""),
        "image_url":         media_item.get("url", ""),
        "image_width":       media_item.get("width", ""),
        "image_height":      media_item.get("height", ""),
        "image_description": entry.get("media_description", ""),
        "image_credit":      entry.get("media_credit", ""),
    }


def is_allowed(article):
    """Filtre : garde uniquement les liens economie-france ou idees-debats."""
    link = article.get("link", "")
    return any(path in link for path in ALLOWED_PATHS)


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
        badge = "Economie" if "economie" in a.get("section", "") else "Idees & Debats"
        lines += [
            f"### [{a['title']}]({a['link']})",
            "",
            f"`{a['pub_date']}` | **{badge}**",
            "",
        ]
        if a["image_url"]:
            lines.append(f"![{a['title']}]({a['image_url']})")
            lines.append("")
        lines += [a["description"], "", "---", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def save_xml(data, path):
    """Genere un fichier RSS 2.0 valide, lisible par tous les lecteurs RSS."""
    rss = Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = data["source"]
    SubElement(channel, "link").text = data["source_url"]
    SubElement(channel, "description").text = "Les Echos - Economie France & Idees-Debats"
    SubElement(channel, "language").text = data["language"]
    SubElement(channel, "lastBuildDate").text = data["last_fetched"]
    SubElement(channel, "copyright").text = data["copyright"]

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", "https://raw.githubusercontent.com/Surmarxisme/rss-lesechos/main/output/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for a in data["articles"]:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = a["title"]
        SubElement(item, "link").text = a["link"]
        SubElement(item, "description").text = a["description"]
        SubElement(item, "pubDate").text = a["pub_date"]
        SubElement(item, "guid", isPermaLink="false").text = a["id"] or a["link"]
        SubElement(item, "category").text = a["section"]
        if a["image_url"]:
            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", a["image_url"])
            enclosure.set("type", "image/jpeg")
            enclosure.set("length", "0")

    tree = ElementTree(rss)
    indent(tree, space="  ")
    with open(path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Fetch les deux sections en parallele
    all_articles = []
    seen_ids = set()

    for feed_cfg in RSS_FEEDS:
        entries = fetch_section(feed_cfg)
        for entry in entries:
            parsed = parse_entry(entry, feed_cfg["section"])
            # Filtre strict sur le chemin du lien
            if not is_allowed(parsed):
                continue
            # Deduplication par id
            uid = parsed["id"] or parsed["link"]
            if uid in seen_ids:
                continue
            seen_ids.add(uid)
            all_articles.append(parsed)

    if not all_articles:
        print("Aucun article recupere apres filtrage", file=sys.stderr)
        sys.exit(1)

    # Trier par date de publication (plus recent en premier)
    all_articles.sort(key=lambda a: a["pub_date"], reverse=True)

    output = {
        "source":       "Les Echos - Economie France & Idees-Debats",
        "source_url":   "https://www.lesechos.fr/economie-france",
        "language":     "fr-FR",
        "copyright":    "Les Echos",
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "last_build":   "",
        "total_items":  len(all_articles),
        "articles":     all_articles,
    }

    save_json(output, os.path.join(OUTPUT_DIR, "feed.json"))
    save_markdown(output, os.path.join(OUTPUT_DIR, "feed.md"))
    save_xml(output, os.path.join(OUTPUT_DIR, "feed.xml"))

    eco = sum(1 for a in all_articles if a["section"] == "economie-france")
    ide = sum(1 for a in all_articles if a["section"] == "idees-debats")
    print(f"OK {len(all_articles)} articles | economie-france: {eco} | idees-debats: {ide}")


if __name__ == "__main__":
    main()

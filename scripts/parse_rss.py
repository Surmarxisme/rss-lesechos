import json
import os
import sys
import feedparser
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

# Google News RSS - Economie France (pas de blocage IP AWS)
RSS_URL = "https://news.google.com/rss/search?q=site:lesechos.fr+economie&hl=fr&gl=FR&ceid=FR:fr"
OUTPUT_DIR = "output"

feedparser.USER_AGENT = "Mozilla/5.0 (compatible; FeedFetcher/1.0)"


def fetch_and_parse():
    feed = feedparser.parse(RSS_URL)
    if feed.bozo and not feed.entries:
        exc = feed.get("bozo_exception", "erreur inconnue")
        print(f"Erreur RSS : {exc}", file=sys.stderr)
        sys.exit(1)
    return feed


def parse_entry(entry):
    media_list = entry.get("media_content") or []
    media_item = media_list[0] if media_list else {}
    tags = entry.get("tags") or []
    category = tags[0].get("term", "") if tags else ""
    return {
        "id":                entry.get("id", ""),
        "title":             (entry.get("title") or "").strip(),
        "description":       (entry.get("summary") or "").strip(),
        "link":              entry.get("link", ""),
        "category":          category,
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
    SubElement(channel, "description").text = "Actualites economiques Les Echos via Google News"
    SubElement(channel, "language").text = data["language"]
    SubElement(channel, "lastBuildDate").text = data["last_fetched"]
    SubElement(channel, "copyright").text = data["copyright"]

    # Lien auto-referentiel Atom (bonne pratique RSS)
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
        if a["category"]:
            SubElement(item, "category").text = a["category"]
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
    feed = fetch_and_parse()

    articles = [parse_entry(e) for e in feed.entries]

    if not articles:
        print("Aucun article recupere", file=sys.stderr)
        sys.exit(1)

    output = {
        "source":       "Les Echos - Economie (via Google News)",
        "source_url":   "https://www.lesechos.fr/economie-france",
        "language":     "fr-FR",
        "copyright":    "Les Echos",
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "last_build":   feed.feed.get("updated", ""),
        "total_items":  len(articles),
        "articles":     articles,
    }

    save_json(output, os.path.join(OUTPUT_DIR, "feed.json"))
    save_markdown(output, os.path.join(OUTPUT_DIR, "feed.md"))
    save_xml(output, os.path.join(OUTPUT_DIR, "feed.xml"))

    print(f"OK {len(articles)} articles | build: {output['last_build']}")
    print(f"Fichiers generes : feed.json, feed.md, feed.xml")


if __name__ == "__main__":
    main()

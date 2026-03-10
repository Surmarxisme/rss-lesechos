# RSS Les Echos - Economie France

![GitHub Actions](https://github.com/Surmarxisme/rss-lesechos/actions/workflows/fetch-rss.yml/badge.svg)

Fetch automatique du flux RSS [Les Echos - Economie](https://www.lesechos.fr/economie-france)
via GitHub Actions. **100 % gratuit** (depot public = minutes illimitees).

## Planning des declenchements (heure de Paris)

| Jour | Horaires |
|------|----------|
| Lundi - Vendredi | 07h00 - 10h00 - 13h00 - 18h00 |
| Samedi - Dimanche | 10h00 |

## Structure du projet

```
rss-lesechos/
├── .github/workflows/fetch-rss.yml  <- Workflow GitHub Actions
├── scripts/parse_rss.py             <- Script de fetch + parsing
├── output/.gitkeep                  <- Dossier versionne
├── output/feed.json                 <- Genere automatiquement
├── output/feed.md                   <- Genere automatiquement
├── requirements.txt
├── .gitignore
└── README.md
```

## Utilisation

1. Forker ce depot (le garder **public**)
2. Aller dans **Actions** - activer les workflows
3. Cliquer **Run workflow** pour un premier test manuel
4. Les fichiers `output/feed.json` et `output/feed.md` se mettent a jour automatiquement

## Exemple d'output JSON

```json
{
  "source": "Les Echos - Economie",
  "last_fetched": "2026-03-10T21:00:00+00:00",
  "total_items": 42
}
```

## Gratuit ?

**0 EUR.** GitHub Actions est gratuit pour les depots publics, sans limite de minutes.

- Depot public = minutes Actions gratuites et illimitees
- Runner `ubuntu-latest` uniquement
- Commits automatiques seulement si le contenu a change (`skip_dirty_check: false`)
- `[skip ci]` dans le message de commit pour eviter les boucles infinies

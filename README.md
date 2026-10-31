# Fire Emblem: Fortune's Weave — 100% planner

A static site with a route order, per-path rosters, build cards for every unit, and Part III squads for 100% completion. Every unit and every class is used at least once.

- `index.html` — home page
- `guide/` — the plan (generated)
- `research/` — source notes from English, Japanese-site and Chinese guides
- `tools/` — data and the generator for `guide/`
- `assets/portraits/` — character portraits (© Nintendo / Intelligent Systems, via Game8); a card falls back to a monogram badge if its image is missing

## Editing the plan

Edit `tools/plan.py` (builds, rosters, squads) or `tools/units.py` (units, classes), then regenerate:

```bash
python3 tools/build_guide.py
```

It prints any unit or class that isn't used anywhere.

## Preview locally

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Publish

GitHub repo → Settings → Pages → Build and deployment → Deploy from a branch → `main`, folder `/ (root)`. The site appears at `https://<user>.github.io/fe18/`.

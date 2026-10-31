"""Render the 100% plan into static HTML pages under guide/.

Run: python3 tools/build_guide.py
"""
from html import escape
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from units import CLASS_CN, CLASSES, LORDS, TIER_ORDER, UNITS  # noqa: E402
from plan import BUILDS, ESHMEL, ESHMEL_NOTES, PART2, PART3, PATHS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "guide"
CSS = "../research/style.css"


def page(title, body, nav_extra=""):
    nav = '<a href="../index.html">Home</a> <a href="index.html">Plan overview</a>' + "".join(
        f' <a href="{p["slug"]}.html">{p["n"]}. {LORDS[p["lord"]]["name"]}</a>' for p in PATHS
    ) + ' <a href="part-2-3.html">Part II &amp; III</a> <a href="../research/index.html">Research</a>' + nav_extra
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<link rel="stylesheet" href="{CSS}">
</head>
<body>
<main>
<nav class="site">{nav}</nav>
{body}
</main>
</body>
</html>
"""


def lord_span(key):
    return f'<span class="lord {key}">{LORDS[key]["name"]}</span>'


def unit_names(name):
    tier, cn, *_ = UNITS[name]
    return f"{escape(name)} <span class=\"meta\">({cn})</span>"


def step_li(cls, when):
    tier, req, unlock = CLASSES[cls]
    extra = f" · {escape(unlock)}" if unlock else ""
    return (f"<li><b>{escape(cls)}</b> <span class=\"chip\">{tier}</span> {escape(when)}<br>"
            f"<span class=\"req\">ranks: {escape(req)}{extra}</span></li>")


def build_card(b, path_n=None):
    name = b["unit"]
    tier, cn, abil, boons, banes = UNITS[name]
    tag = ""
    if b.get("copy") == "final":
        tag = ' <span class="tag-final">final build · merge source</span>'
    elif b.get("copy") == "early":
        tag = ' <span class="tag-early">early copy</span>'
    steps = "".join(step_li(c, w) for c, w in b["steps"])
    rows = [("Joins", b.get("join", "")), ("Role", b.get("role", "")), ("Train", b.get("train", "")),
            ("Gear", b.get("gear", "")), ("Mount etc.", b.get("extra", "")), ("Abilities", abil),
            ("Boons", boons), ("Banes", banes), ("Why", b.get("notes", ""))]
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows if v and v != "—")
    return (f'<div class="card" id="{escape(name.lower().replace(" ", "-"))}">'
            f"<h3>{escape(name)}{tag}</h3>"
            f'<div class="sub">{cn} · Game8 tier {tier}</div>'
            f'<ol class="steps">{steps}</ol><dl>{dl}</dl></div>')


def render_path(p):
    key = p["lord"]
    builds = BUILDS[p["n"]]
    rows = "".join(
        f"<tr><td><a href=\"#{escape(b['unit'].lower().replace(' ', '-'))}\">{escape(b['unit'])}</a></td>"
        f"<td>{b.get('join', '')}</td><td>{escape(b['steps'][-1][0])}</td><td>{escape(b.get('role', ''))}</td>"
        f"<td>{'final' if b.get('copy') == 'final' else 'early copy' if b.get('copy') == 'early' else ''}</td></tr>"
        for b in builds
    )
    checklist = "".join(f"<li>{c}</li>" for c in p["checklist"])
    body = f"""
<h1>Path {p['n']}: {lord_span(key)} <span class="meta">({LORDS[key]['cn']})</span></h1>
<p class="meta">Difficulty: <b>{p['difficulty']}</b></p>
<p>{p['theme']}</p>
<div class="warn">{p['why']}</div>
<h2>Checklist</h2>
<ul>{checklist}</ul>
<h2>Roster ({len(builds)} units)</h2>
<div class="table-wrap"><table>
<tr><th>Unit</th><th>Joins / recruit</th><th>Ends Part I as</th><th>Role</th><th>Copy</th></tr>
{rows}
</table></div>
<p class="meta">Class timing follows Game8's ideal levels: Specialty at Lv20 / Renown 4, Advanced at Lv35 / Renown 8. Megaira refreshes one advanced certificate per chapter (PlayBlackBox), so open it early. Recruit early where you can: units scouted later join at a higher level with weaker stats.</p>
<h2>Builds</h2>
<div class="cards">{''.join(build_card(b, p['n']) for b in builds)}</div>
"""
    return page(f"Path {p['n']} {LORDS[key]['name']}", body)


JOIN_CLASS = {"Eshmel": "Guardian", "Hong Hua": "Ovate", "Troy": "War Monk", "Bertrand": "Warrior",
              "Talimun": "Ovate", "Anatolia": "Ovate", "Orchel": "Bishop", "Centurio": "Dreadnought",
              "Aswan": "Sniper", "Tahonia": "Battlemaster", "Klapka": "Guardian"}


def carried_class(unit, merge):
    """Class a unit brings into Part III: its last Part I/II build, or its join class."""
    if merge:
        b = next(b for b in BUILDS[merge[0]] if b["unit"] == unit)
        return b["steps"][-1][0], f"from {LORDS[PATHS[merge[0] - 1]['lord']]['name']}'s path"
    for n in (4, 3, 2, 1):
        for b in BUILDS[n]:
            if b["unit"] == unit:
                return b["steps"][-1][0], f"from {LORDS[PATHS[n - 1]['lord']]['name']}'s path"
    for b in PART2["builds"]:
        if b["unit"] == unit:
            return b["steps"][-1][0], "from Part II"
    if unit in JOIN_CLASS:
        return JOIN_CLASS[unit], "on join"
    return None, ""


def part3_card(u, squad):
    unit = u["unit"]
    tier, cn, abil, boons, banes = UNITS[unit]
    merge = u.get("merge")
    start, where = carried_class(unit, merge)
    steps = []
    if start and start not in u["pre"] and start != u["master"]:
        steps.append((start, where))
    steps += [(c, "reclass at the exam hall") for c in u["pre"]]
    steps.append((u["master"], "Lv45" if CLASSES[u["master"]][0] == "Master" else "Part III"))
    if u.get("divine"):
        steps.append((u["divine"], "Section 4+, licence item"))
    merge_txt = ""
    if merge:
        names = [LORDS[PATHS[m - 1]["lord"]]["name"] for m in merge]
        merge_txt = f"Merge Causality: {names[0]} copy is the source, + {', '.join(names[1:])} (300 Karma Shards)."
    b = {"unit": unit, "join": f"Squad {squad}", "steps": steps, "gear": u.get("gear", ""),
         "extra": merge_txt, "notes": u.get("note", ""), "copy": "final" if merge else None,
         "train": " · ".join(f"{c}: {CLASSES[c][1]}" for c, _ in steps[-2:] if CLASSES[c][0] in ("Master", "Divine"))}
    return build_card(b)


def render_part23():
    p2_notes = "".join(f"<li>{n}</li>" for n in PART2["notes"])
    p2_cards = "".join(build_card({**b, "join": "Part II"}) for b in PART2["builds"])
    in_p3 = {u["unit"] for sq in PART3 for u in sq["units"]}
    bench = [b["unit"] for n in (1, 2, 3, 4) for b in BUILDS[n] if b["unit"] not in in_p3]
    bench = sorted(set(bench), key=bench.index)
    squads = ""
    for sq in PART3:
        squads += (f"<h3>Squad {escape(sq['squad'])}</h3>"
                   f"<div class=\"cards\">{''.join(part3_card(u, sq['squad']) for u in sq['units'])}</div>")
    body = f"""
<h1>Part II and Part III</h1>
<h2>Part II on {lord_span(PART2['route'])} (Hard)</h2>
<ul>{p2_notes}</ul>
<div class="cards">{p2_cards}</div>
<h2>Part III (Hard): five squads of eight</h2>
<ul>
<li>You start with 2 squads and unlock up to 5. Squads A and B are the core; C–E fill in as they open.</li>
<li>Part I recruits rejoin in Section 2 by talking to them. <b>Merge Causality</b> unlocks after Section 1: Obelisk Chamber → Shrine of Causality, 300 Karma Shards per unit. Pick the later path's copy as the "main stats and class" source; highest stats and all skill ranks/Combat Arts are combined.</li>
<li>Merges here: Guzran, Mu, Nezha, Nuzzuo, Esmeralda (1,500 shards). If shards are tight, Game8 suggests spending them on Boons of Salvation instead; merge Mu and Guzran first.</li>
<li>After merging, don't restart the stage, or the shards are lost (CN).</li>
<li>Master classes need Lv45 and the matching temple restoration where noted. Divine classes open in Section 4; each needs its licence item from the Temple of the Diadem (keys: Heretics' Cave, far east Cougar Woodlands, Giant's-Print Foot, Enno Isle, Sand-Shadow Fort). Only one unit per Divine class.</li>
<li>Bench (already used in Part I; rotate in as needed): {', '.join(bench)}.</li>
<li>Part III is a hit-rate game (CN): fliers are everywhere and dodge well, so stack bow-hit bonuses and accuracy over raw Str/Mag. Collect several Cleansing Blades for Netherworld barriers.</li>
</ul>
{squads}
"""
    return page("Part II and III", body)


def coverage():
    """Where each unit and class is used. Returns (unit_map, class_map)."""
    unit_map, class_map = {}, {}
    for n, builds in BUILDS.items():
        for b in builds:
            unit_map.setdefault(b["unit"], []).append(n)
            for cls, _ in b["steps"]:
                class_map.setdefault(cls, set()).add(f"P{n}")
    for b in PART2["builds"]:
        unit_map.setdefault(b["unit"], []).append("II")
        for cls, _ in b["steps"]:
            class_map.setdefault(cls, set()).add("II")
    for sq in PART3:
        for u in sq["units"]:
            unit_map.setdefault(u["unit"], []).append("III")
            for cls in u["pre"] + [u["master"]] + ([u["divine"]] if u.get("divine") else []):
                class_map.setdefault(cls, set()).add("III")
    for cls in ("Commoner", "Noble"):
        class_map.setdefault(cls, set()).add("P1 checklist")
    return unit_map, class_map


def render_index():
    unit_map, class_map = coverage()
    order = "".join(
        f"<tr><td>{p['n']}</td><td>{lord_span(p['lord'])}</td><td>{p['difficulty']}</td>"
        f"<td>{len(BUILDS[p['n']])}</td><td>{p['why']}</td></tr>" for p in PATHS
    )
    order += ('<tr><td>II</td><td>' + lord_span(PART2["route"]) + '</td><td>Hard</td><td>+2</td>'
              '<td>Creek and Nathan.</td></tr>'
              '<tr><td>III</td><td>All</td><td>Hard</td><td>40</td><td>Merged final builds, Master and Divine classes.</td></tr>')

    def cell(name, n):
        return '<td class="y">●</td>' if n in unit_map.get(name, []) else "<td></td>"

    urows = ""
    for name in UNITS:
        cols = "".join(cell(name, n) for n in (1, 2, 3, 4, "II", "III"))
        urows += f"<tr><td>{escape(name)}</td><td>{UNITS[name][0]}</td>{cols}</tr>"

    crows = ""
    for tier in TIER_ORDER:
        for cls, (t, req, unlock) in CLASSES.items():
            if t != tier:
                continue
            where = ", ".join(sorted(class_map.get(cls, []))) or "<b>MISSING</b>"
            crows += (f"<tr><td>{escape(cls)}</td><td>{CLASS_CN.get(cls, '')}</td><td>{t}</td>"
                      f"<td>{where}</td><td>{escape(unlock)}</td></tr>")

    reused = [u for u, ps in unit_map.items() if len([p for p in ps if isinstance(p, int)]) > 1]
    reuse_rows = ""
    for u in reused:
        paths = [p for p in unit_map[u] if isinstance(p, int)]
        cells = []
        for n in paths:
            b = next(b for b in BUILDS[n] if b["unit"] == u)
            cells.append(f"{lord_span(PATHS[n - 1]['lord'])}: {' → '.join(c for c, _ in b['steps'])}")
        reuse_rows += f"<tr><td>{escape(u)}</td><td>{'<br>'.join(cells)}</td></tr>"

    body = f"""
<h1>Fortune's Weave — 100% team plan</h1>
<p class="meta">火焰纹章 万缕千丝 · built 2026-10-31 from English, Japanese-site and Chinese guides (see <a href="../research/index.html">research</a>).</p>
<h2>Rules this plan follows</h2>
<ul>
<li>Every one of the 63 units is used at least once (46 Part I recruits on the four paths, 2 Part II joiners, 11 Part III-only units, 4 lords).</li>
<li>Paths go easiest → hardest. Paths 1–2 on Normal; then Descend Again to Hard for paths 3–4, Part II and Part III.</li>
<li>Units used on two paths get a different build each time. The early copy runs an off-meta class; the later, harder path runs Game8's recommended line and becomes the Merge Causality source.</li>
<li>Every class is used at least once; weak or utility classes (Light Cavalry, Rogue, Pugilist, Soldier, Blacksmith) sit on the Normal paths.</li>
</ul>
<h2>Order and difficulty</h2>
<div class="table-wrap"><table>
<tr><th>#</th><th>Path</th><th>Difficulty</th><th>Units</th><th>Why here</th></tr>
{order}
</table></div>
<div class="warn">Difficulty can be lowered at the Shrine of Causality any time, but raising it needs <b>Descend Again</b> from the title screen (redo the Prologue; route progress is kept). CN sources say both difficulty and Casual/Classic are set at the Obelisk Hall altar and applied with Descend Again. Hard raises enemy stats and Blessing / rewind costs.</div>

<h2>Eshmel's gender per run</h2>
<div class="table-wrap"><table><tr><th>Run</th><th>Pick</th><th>Why</th></tr>{"".join(f"<tr><td>{e['when']}</td><td><b>{e['pick']}</b></td><td>{e['why']}</td></tr>" for e in ESHMEL)}</table></div>
<ul>{"".join(f"<li>{n}</li>" for n in ESHMEL_NOTES)}</ul>

<h2>Reused units (escalating builds)</h2>
<div class="table-wrap"><table><tr><th>Unit</th><th>Builds, early → final</th></tr>{reuse_rows}</table></div>

<h2>Unit coverage</h2>
<div class="table-wrap"><table>
<tr><th>Unit</th><th>Tier</th><th>1 Cai</th><th>2 Dietrich</th><th>3 Theodora</th><th>4 Leda</th><th>Part II</th><th>Part III</th></tr>
{urows}
</table></div>

<h2>When to promote</h2>
<ul>
<li><b>Default: promote as soon as the exam is a sure pass.</b> Changing class keeps your level and stats, and every level-up uses the new class's growth bonuses. Levels spent in a weaker class are growth you don't get back (allthings.how, CN guides).</li>
<li><b>Exception 1, mastery skills:</b> a fully mastered class gives its skill as a permanent passive you can equip in every later class. If the skill matters for the build, master the class before leaving (allthings.how). Examples: Myrmidon and Shido for Dietrich's crit build, Sniper's bow-hit bonus for Part III archers, Dreadnought's +10 hit when attacked.</li>
<li><b>Farm mastery, not levels:</b> enter a dungeon far below your level, switch the unit into the class, equip a weak weapon of that type and use basic attacks only. Class and weapon EXP rise while stats barely change (CN: NTGame, NGA).</li>
<li><b>Exception 2, growth classes:</b> Charioteer and Elephant Rider boost growths (can't dodge). Sit in them for a while to fix a unit's stats, then move on (Game8).</li>
<li><b>Licences:</b> one exam licence per attempt, used up even on a fail, so only sit an exam at 100% pass chance. Part I gives few Advanced certificates (Megaira refreshes one per chapter), so promote your main units to Advanced in Part I and get the rest to Specialty with their Advanced skill ranks pre-farmed. Part II sets everyone to Lv35 and hands out five Advanced tickets before each battle (GamerSky), so the bench promotes there.</li>
<li><b>Master classes</b> only open in Part III (gods' requests). Levelling past 45 in a good Advanced class while you wait isn't a loss (Game8: use Shido until Swordmaster unlocks).</li>
<li>The Lv20 / Lv35 marks on the build cards are the earliest sensible promotion points, not targets to wait for.</li>
</ul>

<h2>Special classes</h2>
<div class="table-wrap"><table>
<tr><th>Type</th><th>Class → who uses it</th></tr>
<tr><td>One holder at a time</td><td>Dancer → Leda (path 4). Divine: The Blade → Dietrich, The Trident → Theodora, The Cavalier → Cai, The Apsara → Leda, The Avatar → Orchel, The Calamity → Inyoni, The Eternal → Mu, The Godhand → Anatolia (Part III).</td></tr>
<tr><td>Route-locked unlocks</td><td>Caladrius → Cai, Dragoon → Seteth, Troubadour → Ultand (path 1); Blacksmith → Io, Ranger → Jester (path 2); Guardian → Theodora, Cataphract → Tobias (path 3); Dancer → Leda (path 4); Elephant Rider → Benditz (Part III).</td></tr>
<tr><td>Female only</td><td>Wing Soldier → Alexandra, Loretta, Catania, female Eshmel. Celestial Trooper → Catania, Alexandra, female Eshmel.</td></tr>
<tr><td>Fixed-class units</td><td>Klapka stays Guardian, Tahonia stays Battlemaster (they can't reclass); the plan keeps both in those classes.</td></tr>
<tr><td>Character-unique</td><td>None. The Japanese class list counts 60 classes (2 basic, 5 beginner, 12 specialty, 17 advanced, 16 master, 8 divine), all shared; the Savior just starts as Guardian.</td></tr>
<tr><td>DLC</td><td>No DLC classes reported. Expansion Pass part 1 (10/15) adds one weapon per lord route; part 2 (winter) adds Aurora, Smyrnos and Jurah as Part III units — not in this plan yet.</td></tr>
</table></div>

<h2>Class coverage</h2>
<p class="meta">P1–P4 = Part I paths, II/III = later parts. Beginner and Specialty classes are the steps units pass through on the way to Advanced.</p>
<div class="table-wrap"><table>
<tr><th>Class</th><th>CN name</th><th>Tier</th><th>Used on</th><th>Unlock</th></tr>
{crows}
</table></div>

<h2>Caveats</h2>
<ul>
<li>Recruit numbers come from Game8 EN/JP, GamerSky and Pocket Tactics (Sept–Oct 2026). A 10/15 patch may have changed some; check in game.</li>
<li>Most EN guides suggest Cai → Theodora → Dietrich → Leda. This plan swaps Dietrich and Theodora so Blacksmith (Dietrich-only, weakest class) lands on a Normal path and the strongest lord eases the second run; Theodora's defensive kit is the gentler Hard opener.</li>
<li>Game8 doesn't list requirements for Soldier, Pugilist or Blacksmith; their placement follows each unit's boons.</li>
<li>Master unlock temples marked "unverified" came from a summarised part of Game8's class page.</li>
<li>Deployment limits per map aren't confirmed, so rosters of 13–15 assume some rotation.</li>
</ul>
"""
    return page("Fortune's Weave 100% plan", body)


def check():
    unit_map, class_map = coverage()
    missing_units = [u for u in UNITS if u not in unit_map]
    missing_classes = [c for c in CLASSES if c not in class_map]
    for n, builds in BUILDS.items():
        for b in builds:
            for cls, _ in b["steps"]:
                assert cls in CLASSES, f"unknown class {cls} for {b['unit']}"
            assert b["unit"] in UNITS, f"unknown unit {b['unit']}"
    divine = [u["divine"] for sq in PART3 for u in sq["units"] if u.get("divine")]
    assert len(divine) == len(set(divine)), "a Divine class is assigned twice"
    sizes = [len(sq["units"]) for sq in PART3]
    return missing_units, missing_classes, sizes


def main():
    OUT.mkdir(exist_ok=True)
    missing_units, missing_classes, sizes = check()
    (OUT / "index.html").write_text(render_index())
    for p in PATHS:
        (OUT / f"{p['slug']}.html").write_text(render_path(p))
    (OUT / "part-2-3.html").write_text(render_part23())
    print("missing units:", missing_units)
    print("missing classes:", missing_classes)
    print("squad sizes:", sizes)


if __name__ == "__main__":
    main()

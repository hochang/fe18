"""Render the 100% plan into static HTML pages under guide/.

Run: python3 tools/build_guide.py
"""
from html import escape
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from units import CLASS_CN, CLASSES, LORDS, TIER_ORDER, UNITS  # noqa: E402
from plan import BUILDS, ESHMEL, ESHMEL_NOTES, PART2, PART3, PATHS, RECRUIT, WALKTHROUGH  # noqa: E402
from skills import (CLASS_GROWTH, CLASS_ROLE, FEMALE, FEMALE_ONLY, MASTERY, ROLE, STATS,  # noqa: E402
                    UNIT_GROWTH, UNLOCK_PATH)
import re  # noqa: E402
from supports import ENDINGS, GIFTS, PREFER  # noqa: E402
from gifts import GIFT_PREFS  # noqa: E402

FAIRE = {"Sword": "Swordfaire", "Spear": "Spearfaire", "Axe": "Axefaire", "Bow": "Bowfaire",
         "Gauntlet": "Fistfaire", "Black Magic": "Black-Magic Mastery", "White Magic": "White-Magic Mastery"}

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "guide"
CHARS = OUT / "characters"
CSS_VER = __import__("hashlib").sha1((ROOT / "research" / "style.css").read_bytes()).hexdigest()[:8]


def site_nav(prefix):
    """The shared nav bar. prefix is the path from the page to the site root ('', '../' or '/fe18/')."""
    items = [("index.html", "Home"), ("guide/index.html", "Plan overview")]
    items += [(f"guide/{p['slug']}.html", f"{p['n']}. {LORDS[p['lord']]['name']}") for p in PATHS]
    items += [("guide/part-2-3.html", "Part II &amp; III"), ("guide/characters/index.html", "Characters"),
              ("guide/skills.html", "Skills"), ("guide/supports.html", "Supports"), ("research/index.html", "Research")]
    return '<nav class="site">' + " ".join(f'<a href="{prefix}{h}">{t}</a>' for h, t in items) + "</nav>"


def sync_static_navs():
    """Put the shared nav on the hand-written pages (home, research, 404)."""
    targets = [(ROOT / "index.html", ""), (ROOT / "404.html", "/fe18/")]
    targets += [(f, "../") for f in sorted((ROOT / "research").glob("*.html"))]
    for f, prefix in targets:
        s = f.read_text(encoding="utf-8")
        nav = site_nav(prefix)
        s = re.sub(r'href="([^"]*style\.css)(\?v=\w+)?"', lambda m: f'href="{m.group(1)}?v={CSS_VER}"', s)
        if '<nav class="site">' in s:
            s = re.sub(r'<nav class="site">.*?</nav>', lambda m: nav, s, count=1, flags=re.S)
        else:
            s = s.replace("<main>\n", "<main>\n" + nav + "\n", 1)
        f.write_text(s, encoding="utf-8")


def page(title, body, nav_extra="", depth=1):
    up = "../" * depth
    nav = site_nav(up)[len('<nav class="site">'):-len("</nav>")] + nav_extra
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<link rel="stylesheet" href="{up}research/style.css?v={CSS_VER}">
</head>
<body>
<main>
<nav class="site">{nav}</nav>
{body}
<p class="meta" style="margin-top:3rem">Fan-made planner, not affiliated with Nintendo or Intelligent Systems. Character portraits © Nintendo / Intelligent Systems, via Game8.</p>
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


def growth(unit, cls, stat):
    if cls not in CLASS_GROWTH:
        return None
    i = STATS.index(stat)
    return UNIT_GROWTH[unit][i] + CLASS_GROWTH[cls][i]


def class_available(cls, unit, path_n):
    """Whether a unit can sit in this class on this path (path_n 'III' = Part III)."""
    tier = CLASSES[cls][0]
    if cls in FEMALE_ONLY and unit not in FEMALE:
        return False
    if path_n == "III":
        return True
    if tier in ("Master", "Divine") or cls == "Elephant Rider":
        return False
    return UNLOCK_PATH.get(cls, 0) <= (path_n if isinstance(path_n, int) else 4)


SKILL_NAME = {"White": "White Magic", "Black": "Black Magic"}


def blocked_by_bane(cls, unit):
    """True if a required skill of the class is one of the unit's banes (every alternative)."""
    banes = {x.strip() for x in UNITS[unit][4].split(",")}
    for part in re.split(r"[;,]", CLASSES[cls][1]):
        alts = [re.sub(r"\s+[A-ES]\+?$", "", a.strip()) for a in part.split("/")]
        alts = [SKILL_NAME.get(a, a) for a in alts if a]
        if alts and all(a in banes for a in alts):
            return True
    return False


def final_copy(unit, path_n):
    for n in range(path_n + 1, 5):
        for b in BUILDS[n]:
            if b["unit"] == unit and b.get("copy") == "final":
                return n, b
    return None, None


def personal_abilities(abil):
    return [a.strip() for a in re.sub(r"\([^)]*\)", "", abil).split(",") if a.strip()]


def masteries(b, path_n):
    """Classes this build masters on its path, and extra classes to farm for their skills."""
    unit, copy = b["unit"], b.get("copy")
    classes = [c for c, _ in b["steps"]]
    pack = ROLE[CLASS_ROLE.get(classes[-1], "sword")][1]
    kept = [c for c in classes if c in MASTERY and CLASSES[c][0] not in ("Beginner", "Basic")]
    limit = 1 if copy == "early" else 3 if (copy == "final" or path_n == "III") else 2
    farm = [c for c in pack if c not in classes and class_available(c, unit, path_n)
            and CLASSES[c][0] not in ("Beginner", "Basic") and not blocked_by_bane(c, unit)][:limit]
    return [kept, farm]


def skill_rows(b, path_n):
    """Level-in growths, masteries to keep and farm, and an equip order for one build."""
    unit = b["unit"]
    classes = [c for c, _ in b["steps"]]
    role = CLASS_ROLE.get(classes[-1], "sword")
    keys, pack, weapon, extra = ROLE[role]
    copy = b.get("copy")
    rows = []

    lv = []
    for c in classes:
        g = [growth(unit, c, k) for k in keys]
        if None in g:
            continue
        lv.append(f"{escape(c)}: " + " · ".join(f"{k} {v}%" for k, v in zip(keys, g)))
    if lv:
        rows.append(("Level in", "<br>".join(lv)))

    kept, farm = masteries(b, path_n)
    inherited = []
    for m in b.get("carry") or []:
        eb = next(x for x in BUILDS[m] if x["unit"] == unit)
        inherited += [c for c in sum(masteries(eb, m), []) if c not in kept and c not in inherited]
    farm = [c for c in farm if c not in inherited]
    if inherited:
        rows.append(("Carried in", "; ".join(f"{escape(c)} → <b>{MASTERY[c][0]}</b>" for c in inherited)
                     + " <span class=\"meta\">— mastered on Part I paths</span>"))
    early = set()
    if copy == "final" and isinstance(path_n, int):
        for n in range(1, path_n):
            for eb in BUILDS[n]:
                if eb["unit"] == unit:
                    early |= set(sum(masteries(eb, n), []))
    if kept:
        rows.append(("Master here", "; ".join(f"{escape(c)} → <b>{MASTERY[c][0]}</b> ({MASTERY[c][1]})" for c in kept)))
    if farm:
        rows.append(("Farm only", "; ".join(f"{escape(c)} → <b>{MASTERY[c][0]}</b> ({MASTERY[c][1]})"
                                             + (" — also arrives via the Part III merge" if c in early else "") for c in farm)
                     + " <span class=\"meta\">— low-level dungeon, weak weapon, basic attacks, so it costs almost no levels</span>"))

    owned = kept + farm + inherited
    ranked = [c for c in pack if c in owned] + [c for c in owned if c not in pack]
    top = []
    for c in reversed(classes):
        if CLASSES.get(c, ("",))[0] in ("Master", "Divine") and c in MASTERY:
            top.append(MASTERY[c][0])
    top += [MASTERY[c][0] for c in ranked if MASTERY[c][0] not in top]
    faire = " or ".join(FAIRE[w.strip()] for w in weapon.split(" or ") if w.strip() in FAIRE)
    if copy == "final" or path_n == "III":
        rank_ability = f"{faire} at S+ (Hit/Avo +10, Atk +3)"
    else:
        rank_ability = f"{weapon} Lv. 3 at B+ (Hit/Avo +5)"
    equip = personal_abilities(UNITS[unit][2]) + top[:3] + [rank_ability]
    if extra:
        equip.append(extra)
    rows.append(("Equip order", " → ".join(escape(e) for e in equip)))

    if copy == "early":
        n, fb = final_copy(unit, path_n)
        if fb:
            mine, theirs = classes[-1], fb["steps"][-1][0]
            better = [k for k in STATS if k != "Cha" and
                      CLASS_GROWTH[mine][STATS.index(k)] - CLASS_GROWTH[theirs][STATS.index(k)] >= 10]
            if better:
                rows.append(("Merge gain", f"{escape(mine)} grows {', '.join(better)} faster than the final copy's "
                             f"{escape(theirs)}; merge keeps the higher value, and these masteries carry over."))
    return rows


PORTRAITS = ROOT / "assets" / "portraits"
LORD_COLOR = {"cai": "var(--cai)", "dietrich": "var(--dietrich)", "theodora": "var(--theodora)",
              "leda": "var(--leda)", None: "var(--accent)"}


def slug(name):
    return name.lower().replace(" ", "-")


def home_lord(name):
    for p in PATHS:
        if any(b["unit"] == name for b in BUILDS[p["n"]]):
            return p["lord"]
    return None


def avatar(name, up="../", large=False):
    """Portrait from assets/portraits/<slug>.(webp|png|jpg) if present, else a monogram badge."""
    cls = "avatar avatar-lg" if large else "avatar"
    w, h = (140, 112) if large else (70, 56)
    for ext in ("webp", "png", "jpg"):
        if (PORTRAITS / f"{slug(name)}.{ext}").exists():
            return (f'<img class="{cls}" src="{up}assets/portraits/{slug(name)}.{ext}" '
                    f'alt="{escape(name)}" loading="lazy" width="{w}" height="{h}">')
    words = name.split()
    initials = "".join(w[0] for w in words[:2]) if len(words) > 1 else name[:2]
    color = LORD_COLOR[home_lord(name)]
    return (f'<svg class="{cls}" viewBox="0 0 56 56" role="img" aria-label="{escape(name)}">'
            f'<circle cx="28" cy="28" r="26" fill="var(--chip)" stroke="{color}" stroke-width="3"/>'
            f'<text x="28" y="34" text-anchor="middle" font-size="18" font-weight="700" fill="{color}">'
            f'{escape(initials)}</text></svg>')


def copy_tag(b):
    if b.get("copy") == "final":
        return ' <span class="tag-final">final build · merge source</span>'
    if b.get("copy") == "early":
        return ' <span class="tag-early">early copy</span>'
    return ""


def build_details(b, path_n=None):
    """Class steps plus the detail rows of one build (no header)."""
    steps = "".join(step_li(c, w) for c, w in b["steps"])
    rows = [("Joins", b.get("join", "")), ("Role", b.get("role", "")), ("Train", b.get("train", "")),
            ("Gear", b.get("gear", "")), ("Mount etc.", b.get("extra", "")), ("Why", b.get("notes", ""))]
    if path_n is not None:
        rows[5:5] = skill_rows(b, path_n)
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows if v and v != "—")
    return f'<ol class="steps">{steps}</ol><dl>{dl}</dl>'


def char_href(name, up=""):
    return f"{up}characters/{slug(name)}.html"


def char_link(name, up="", frag=""):
    return f'<a href="{char_href(name, up)}{frag}">{escape(name)}</a>'


def mini_card(name, line, href, up="../"):
    """Compact linked card: portrait, name, one line of build summary."""
    tier, cn, *_ = UNITS[name]
    return (f'<a class="mini" href="{href}">{avatar(name, up)}<span><b>{escape(name)}</b> '
            f'<span class="meta">{cn}</span><br><span class="meta">{line}</span></span></a>')


def anchor(name):
    return char_link(name)


def render_walkthrough(p):
    """Recruit and bond walkthrough for one path, if the plan has one."""
    n, key = p["n"], p["lord"]
    w = WALKTHROUGH.get(n)
    if not w:
        return ""
    lord = LORDS[key]["name"]
    rules = "".join(f"<li>{r}</li>" for r in w["rules"])
    rec = "".join(
        f"<tr><td>{anchor(u)}</td><td>{a}</td><td>{s_}</td><td>{r}</td><td>{escape(item)}</td>"
        f"<td>{escape(how)}</td><td><b>{ch}</b></td></tr>"
        for u, a, s_, r, item, how, ch in RECRUIT.get(n, []))
    chapters = ""
    for ch, turns, dates, renown, steps in w["chapters"]:
        meta = " · ".join(x for x in (turns, dates, f"expected Renown {renown}" if renown != "—" else "") if x and x != "—")
        chapters += (f"<h3>{ch} <span class=\"meta\">{meta}</span></h3><ul>"
                     + "".join(f"<li>{st}</li>" for st in steps) + "</ul>")

    # Extra bonds: paired endings touching this path, and the lord's Part III squad-mates.
    pairing, squad, paths, _ = best_pairing()
    here = {b["unit"] for b in BUILDS[n]}
    chosen = {frozenset(e[:2]) for e in pairing}
    extra = []
    for a, b, sc, rom in sorted(pairing, key=lambda e: -((e[0] in here) + (e[1] in here))):
        if a in here or b in here:
            rivals = sorted({other for x in (a, b) for (e1, e2, _) in ENDINGS if x in (e1, e2)
                             for other in [f"{x}–{e2 if e1 == x else e1}"]
                             if frozenset((e1, e2)) not in chosen and "Eshmel" not in (e1, e2)})
            keep = f" Keep it above {', '.join(rivals)}." if rivals else ""
            where = "both are here" if a in here and b in here else "only one of them is on this path; raise it with meals and gifts"
            extra.append(f"<b>{escape(a)} + {escape(b)}</b> ({'romantic' if rom else 'platonic or vague'} ending; {where}): "
                         f"get them to A support and watch the conversation.{escape(keep)}")
    lord_squad = squad.get(lord)
    mates = [u["unit"] for sq in PART3 if sq["squad"] == lord_squad for u in sq["units"]]
    away = [m for m in mates if m not in here and m != lord and m not in PART3_ONLY_NAMES]
    if away:
        extra.append(f"<b>Part III squad-mates</b> ({escape(lord_squad)}): {', '.join(escape(m) for m in away)} fight next to {lord} "
                     f"in Part III but aren't recruited on this path. A few meals with {lord} now give side-by-side support buffs later.")
    extra.append("Three-person meals: inviting both partners of a pair together may also raise support between the two guests. "
                 "That isn't confirmed, so check the support screen after one meal before relying on it.")
    extra.append("Don't overshoot: a unit's ending goes to whoever they share the most support points with.")
    shopping = "".join(f"<tr><td>{escape(a)}</td><td>{escape(b)}</td><td>{escape(c)}</td></tr>" for a, b, c in w["shopping"])
    notes = "".join(f"<li>{x}</li>" for x in w["notes"])
    return f"""
<h2>Recruit and bond walkthrough</h2>
<ul>{rules}</ul>
<h3>Who, what and when</h3>
<div class="table-wrap"><table>
<tr><th>Unit</th><th>Appears</th><th>Support</th><th>Renown</th><th>Item or task</th><th>Where / how</th><th>Recruit in</th></tr>
{rec}
</table></div>
{chapters}
<h3>Extra bonds (from Ch8, once recruiting is done)</h3>
<p>Spare meal seats are worth spending only on these. Raising {lord}'s support with a unit doesn't help recruit them on another lord's path: that checks support with that path's lord.</p>
<ul>{"".join(f"<li>{x}</li>" for x in extra)}</ul>
<h3>Shopping list</h3>
<div class="table-wrap"><table><tr><th>Item</th><th>Where</th><th>Cost</th></tr>{shopping}</table></div>
<p class="meta">Cai's kindness quests pay 550–7,000G each, so gold isn't the limit; Support 3 is.</p>
<h3>Caveats</h3>
<ul>{notes}</ul>
"""


def render_path(p):
    key = p["lord"]
    builds = BUILDS[p["n"]]
    rows = "".join(
        f"<tr><td>{char_link(b['unit'], frag='#path-' + str(p['n']))}</td>"
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
{render_walkthrough(p)}
<h2>Roster ({len(builds)} units)</h2>
<div class="table-wrap"><table>
<tr><th>Unit</th><th>Joins / recruit</th><th>Ends Part I as</th><th>Role</th><th>Copy</th></tr>
{rows}
</table></div>
<p class="meta">Class timing follows Game8's ideal levels: Specialty at Lv20 / Renown 4, Advanced at Lv35 / Renown 8. Megaira refreshes one advanced certificate per chapter (PlayBlackBox), so open it early. Recruit early where you can: units scouted later join at a higher level with weaker stats.</p>
<h2>Builds</h2>
<p class="meta">Each character's full build (class steps, levelling, masteries, equip order, gifts) is on their own page.</p>
<div class="cards compact">{''.join(mini_card(b['unit'], ' → '.join(c for c, _ in b['steps']) + copy_tag(b), char_href(b['unit']) + f"#path-{p['n']}") for b in builds)}</div>
"""
    return page(f"Path {p['n']} {LORDS[key]['name']}", body)


PART3_ONLY_NAMES = {"Eshmel", "Hong Hua", "Troy", "Bertrand", "Talimun", "Anatolia", "Orchel",
                    "Centurio", "Aswan", "Tahonia", "Klapka", "Creek", "Nathan"}

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


def part3_build(u, squad):
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
    carry = merge or [n for n in (1, 2, 3, 4) if any(x["unit"] == unit for x in BUILDS[n])]
    b = {"unit": unit, "join": f"Squad {squad}", "steps": steps, "gear": u.get("gear", ""), "carry": carry,
         "extra": merge_txt, "notes": u.get("note", ""), "copy": "final" if merge else None,
         "train": " · ".join(f"{c}: {CLASSES[c][1]}" for c, _ in steps[-2:] if CLASSES[c][0] in ("Master", "Divine"))}
    return b


def render_part23():
    p2_notes = "".join(f"<li>{n}</li>" for n in PART2["notes"])
    p2_cards = "".join(mini_card(b["unit"], " → ".join(c for c, _ in b["steps"]), char_href(b["unit"]) + "#part-2")
                       for b in PART2["builds"])
    in_p3 = {u["unit"] for sq in PART3 for u in sq["units"]}
    bench = [b["unit"] for n in (1, 2, 3, 4) for b in BUILDS[n] if b["unit"] not in in_p3]
    bench = sorted(set(bench), key=bench.index)
    squads = ""
    for sq in PART3:
        cards = "".join(mini_card(u["unit"], escape(u["master"]) + (f" → {escape(u['divine'])}" if u.get("divine") else "")
                                  + (' <span class="tag-final">merged</span>' if u.get("merge") else ""),
                                  char_href(u["unit"]) + "#part-3") for u in sq["units"])
        squads += f"<h3>Squad {escape(sq['squad'])}</h3><div class=\"cards compact\">{cards}</div>"
    body = f"""
<h1>Part II and Part III</h1>
<h2>Part II on {lord_span(PART2['route'])} (Hard)</h2>
<ul>{p2_notes}</ul>
<div class="cards compact">{p2_cards}</div>
<h2>Part III (Hard): five squads of eight</h2>
<ul>
<li>You start with 2 squads and unlock up to 5. Squads A and B are the core; C–E fill in as they open.</li>
<li>Part I recruits rejoin in Section 2 by talking to them. <b>Merge Causality</b> unlocks after Section 1: Obelisk Chamber → Shrine of Causality, 300 Karma Shards per unit. Pick the later path's copy as the "main stats and class" source; highest stats and all skill ranks/Combat Arts are combined.</li>
<li>Merges here: Mu (four copies, three merges), Guzran, Esmeralda (about 1,500 shards). If shards are tight, Game8 suggests spending them on Boons of Salvation instead; merge Mu and Guzran first.</li>
<li>After merging, don't restart the stage, or the shards are lost (CN).</li>
<li>Master classes need Lv45 and the matching temple restoration where noted. Divine classes open in Section 4; each needs its licence item from the Temple of the Diadem (keys: Heretics' Cave, far east Cougar Woodlands, Giant's-Print Foot, Enno Isle, Sand-Shadow Fort). Only one unit per Divine class.</li>
<li>Bench (already used in Part I; rotate in as needed): {', '.join(char_link(b) for b in bench)}.</li>
<li>Part III is a hit-rate game (CN): fliers are everywhere and dodge well, so stack bow-hit bonuses and accuracy over raw Str/Mag. Collect several Cleansing Blades for Netherworld barriers.</li>
</ul>
{squads}
"""
    return page("Part II and III", body)


def render_skills():
    head = "".join(f"<th>{k}</th>" for k in STATS)
    crows = ""
    for tier in TIER_ORDER:
        for cls, (t, req, unlock) in CLASSES.items():
            if t != tier:
                continue
            g = CLASS_GROWTH.get(cls)
            cells = "".join(f"<td>{v:+d}</td>" for v in g) if g else f"<td colspan=\"{len(STATS)}\">not listed</td>"
            m = MASTERY.get(cls, ("", ""))
            crows += (f"<tr><td>{escape(cls)}</td><td>{CLASS_CN.get(cls, '')}</td><td>{t}</td>"
                      f"<td><b>{escape(m[0])}</b><br><span class=\"meta\">{escape(m[1])}</span></td>{cells}</tr>")
    urows = "".join(f"<tr><td>{char_link(u)}</td><td>{UNITS[u][1]}</td>" + "".join(f"<td>{v}</td>" for v in g) + "</tr>"
                    for u, g in UNIT_GROWTH.items())
    body = f"""
<h1>Masteries and growth rates</h1>
<p class="meta">Masteries: Game8 class and ability pages. Growths: Keengamer (2026-09-28). Final growth = character growth + class modifier, rolled per stat each level.</p>
<h2>How masteries and levelling fit together</h2>
<ul>
<li>Fully mastering a class gives its mastery ability for good: you can equip it in any later class (Game8, allthings.how). Merge Causality in Part III carries every copy's masteries to the merged unit.</li>
<li>Every level uses the growth modifiers of the class you're in, so spend real levels in the class whose growths fit the unit's role. That's the <b>Level in</b> line on each build card.</li>
<li>Masteries from other classes (<b>Farm only</b> on the cards) are earned in a dungeon far below your level: switch into the class, equip a weak weapon of its type and use basic attacks, not one-hit kills. Class experience rises while you gain few levels (CN: NTGame, NGA).</li>
<li>Early copies on Normal paths are the cheapest place to bank extra masteries; they flow into the final copy at the Part III merge.</li>
<li>Equip in this order (Game8): personal Lv20/Lv35 abilities, the class's own mastery, off-class masteries, then weapon-rank abilities like Swordfaire. Mounted units can't use infantry-only abilities and vice versa. The ability slot count isn't confirmed by any source.</li>
</ul>
<h2>Weapon-rank abilities</h2>
<div class="table-wrap"><table>
<tr><th>Rank</th><th>Ability</th><th>Effect with that weapon</th></tr>
<tr><td>D+</td><td>&lt;Weapon&gt; Lv. 1</td><td>Hit +3</td></tr>
<tr><td>C+</td><td>Lv. 2</td><td>Hit +5</td></tr>
<tr><td>B+</td><td>Lv. 3</td><td>Hit/Avo +5</td></tr>
<tr><td>A+</td><td>Lv. 4</td><td>Hit/Avo +7</td></tr>
<tr><td>S</td><td>Lv. 5</td><td>Hit/Avo +10</td></tr>
<tr><td>S+</td><td>Swordfaire / Spearfaire / Axefaire / Bowfaire / Fistfaire / Black- or White-Magic Mastery</td><td>Hit/Avo +10, Atk +3</td></tr>
</table></div>
<p class="meta">Rank-to-level pairing is inferred from Game8's page layout. Other skill abilities worth noting: Read the Winds (Flying D, Avo +10 vs bows), Heavy Break (Armored, Theodora and Esmeralda), Evasion, Infantry Move.</p>
<h2>Classes: mastery ability and growth modifiers</h2>
<div class="table-wrap"><table>
<tr><th>Class</th><th>CN</th><th>Tier</th><th>Mastery</th>{head}</tr>
{crows}
</table></div>
<h2>Character growth rates</h2>
<div class="table-wrap"><table>
<tr><th>Unit</th><th>CN</th>{head}</tr>
{urows}
</table></div>
<p class="meta">Mu's row includes Signs of Growth (+20 to each growth).</p>
<h2>Sources</h2>
<ul class="sources">
<li><a href="https://game8.co/games/Fire-Emblem-Fortunes-Weave/archives/620256">Game8 — class list</a></li>
<li><a href="https://game8.co/games/Fire-Emblem-Fortunes-Weave/archives/623691">Game8 — all abilities</a></li>
<li><a href="https://game8.co/games/Fire-Emblem-Fortunes-Weave/archives/631539">Game8 — best abilities to equip</a></li>
<li><a href="https://www.keengamer.com/articles/guides/fire-emblem-fortunes-weave-growth-rates-for-all-characters-and-classes/">Keengamer — growth rates</a></li>
<li><a href="https://allthings.how/fire-emblem-fortune-s-weave-class-guide-all-tiers-and-masteries/">allthings.how — class guide and masteries</a></li>
<li><a href="https://ntgame.com/fire-emblem-wanlvqiansi/growth/">NTGame — growth and mastery (CN)</a></li>
</ul>
"""
    return page("Masteries and Growths", body)


def best_pairing():
    """Maximum set of paired endings with no unit used twice.

    Ranked by number of pairs, then by how much the partners fight together:
    same Part III squad +3, a shared Part I path +2, both in Part III +1, romantic +0.5.
    """
    squad = {u["unit"]: sq["squad"] for sq in PART3 for u in sq["units"]}
    paths = {}
    for n, bs in BUILDS.items():
        for b in bs:
            paths.setdefault(b["unit"], set()).add(n)

    def score(a, b, rom):
        sc = 3 if squad.get(a) and squad.get(a) == squad.get(b) else 0
        sc += 2 if paths.get(a, set()) & paths.get(b, set()) else 0
        sc += 1 if a in squad and b in squad else 0
        return sc + (0.5 if rom else 0) + PREFER.get((a, b), PREFER.get((b, a), 0))

    edges = [(a, b, score(a, b, r), r) for a, b, r in ENDINGS if a in UNITS and b in UNITS]
    adj = {}
    for e in edges:
        for n in e[:2]:
            adj.setdefault(n, []).append(e)
    best = [(-1, -1.0), []]

    def other(e, n):
        return e[1] if e[0] == n else e[0]

    def solve(free, chosen, cnt, sc):
        live = [n for n in free if any(other(e, n) in free for e in adj[n])]
        if cnt + len(live) // 2 < best[0][0]:
            return
        if not live:
            if (cnt, sc) > best[0]:
                best[0], best[1] = (cnt, sc), list(chosen)
            return
        n = min(live, key=lambda x: sum(other(e, x) in free for e in adj[x]))
        for e in sorted(adj[n], key=lambda e: -e[2]):
            if other(e, n) in free:
                chosen.append(e)
                solve(free - {n, other(e, n)}, chosen, cnt + 1, sc + e[2])
                chosen.pop()
        solve(free - {n}, chosen, cnt, sc)

    solve(frozenset(adj), [], 0, 0.0)
    return best[1], squad, paths, set(adj)


def render_supports():
    pairing, squad, paths, has_ending = best_pairing()
    pairing.sort(key=lambda e: -e[2])
    matched = {n for e in pairing for n in e[:2]}

    def together(a, b):
        bits = []
        if squad.get(a) and squad.get(a) == squad.get(b):
            bits.append(f"Part III Squad {escape(squad[a])}")
        for n in sorted(paths.get(a, set()) & paths.get(b, set())):
            bits.append(f"Path {n} ({LORDS[PATHS[n - 1]['lord']]['name']})")
        return ", ".join(bits) or "Not deployed together — raise it with meals and gifts"

    def who(n):
        return f'<div class="card-head">{avatar(n)}<div><b>{char_link(n)}</b><br><span class="meta">{UNITS[n][1]}</span></div></div>'

    rows = ""
    for a, b, sc, rom in pairing:
        gifts = "<br>".join(f"<b>{escape(x)}</b>: {escape(GIFTS[x])}" for x in (a, b) if x in GIFTS)
        kind = "Romantic" if rom else "Platonic or vague"
        if "Eshmel" in (a, b):
            kind = "Eshmel's pick (Support Level 5)"
        rows += (f"<tr><td>{who(a)}</td><td>{who(b)}</td><td>{kind}</td>"
                 f"<td>{together(a, b)}</td><td>{gifts}</td></tr>")
    only_eshmel = sorted(n for n in has_ending - matched if n != "Eshmel")
    no_ending = sorted(set(UNITS) - has_ending)
    body = f"""
<h1>Supports and paired endings</h1>
<p class="meta">Pairs from Game8's paired-endings list (work in progress, read 2026-10-31). The pairing below is computed by the generator from the current roster, so it updates when the plan changes.</p>
<h2>How it works</h2>
<ul>
<li><b>No marriage:</b> there are no S supports, no marriage system and no child units (Game8).</li>
<li><b>Paired endings:</b> a character's ending pairs them with whoever they share the most support points with, but only if that pair has unlocked and watched its A support. Some endings are romantic (marriage, proposal, children), some vague, some platonic.</li>
<li><b>Eshmel:</b> after the final battle you pick Eshmel's partner from anyone at Support Level 5. 48 units qualify; Part II/III joiners (except Hong Hua) and Seteth, Kiroc and Nuzzuo can't. No source mentions a gender requirement.</li>
<li><b>Combat:</b> units with higher support buff each other when fighting side by side; the bonus grows with support level (Game8). No source gives the numbers. That's why the pairing below prefers partners who share a squad or path.</li>
<li><b>Lords</b> need their own Part I path completed to get an ending.</li>
</ul>
<h2>Best pairing: {len(pairing)} pairs</h2>
<p>{len(pairing)} is the most possible: no unit is in two pairs, and the {len(only_eshmel)} units listed further down have Eshmel as their only ending partner, while Eshmel can take one. Ties go to partners who fight together (same Part III squad, then same Part I path), then romantic endings.</p>
<div class="table-wrap"><table>
<tr><th>Unit</th><th>Partner</th><th>Ending</th><th>Fight together in</th><th>Favourite gifts</th></tr>
{rows}
</table></div>
<p class="meta">Part III squads were adjusted for this: Olympia moved to Squad D with Leda, Loretta to Squad C with Seteth, Jester to Squad E with Halvin.</p>
<h2>Raising support quickly</h2>
<ul>
<li>Meals at an inn (three units at a time) are half price on Sundays and holidays. Gifts and meals also work on units not yet recruited.</li>
<li>Restarting a chapter keeps support points: on a long chapter, eat the three meals, auto-activity to the next Sunday, repeat, then restart (Game8, NGA).</li>
<li>Fight side by side, heal or support with arts, and use Link attacks in dungeon clashes.</li>
<li>Gifts many units love: Tales of Adventure, Strategy Manuscript, History of a Master, Portrait of Yu Phas, Volcano Ghosh. A gift on a unit's birthday always gets the best reaction.</li>
<li>Bird Time raises Eshmel's support with everyone.</li>
<li>Pairs on different paths: supports are shared across the save, so build them with meals and gifts on whichever path both are around.</li>
<li>Don't max a unit's support with someone else past their partner's, or the ending goes to the other unit.</li>
</ul>
<h2>Left without a partner</h2>
<p><b>Only partner is Eshmel</b> (taken by {escape(next((other for e in pairing if "Eshmel" in e[:2] for other in e[:2] if other != "Eshmel"), "—"))}): {", ".join(escape(n) for n in only_eshmel)}.</p>
<p>Eshmel's slot is the flexible one: swapping Eshmel's partner for any unit in that list keeps the same number of pairs. Pick Theodora instead if you want all four lords to get an ending; the plan prefers a squad-mate for the side-by-side support buffs.</p>
<p><b>No paired ending listed</b> (the Game8 page is unfinished, and Bertrand, Talimun, Orchel and Anatolia may get endings with the Expansion Pass): {", ".join(escape(n) for n in no_ending)}.</p>
<h2>Sources</h2>
<ul class="sources">
<li><a href="https://game8.co/games/Fire-Emblem-Fortunes-Weave/archives/628208">Game8 — all paired endings</a></li>
<li><a href="https://game8.co/games/Fire-Emblem-Fortunes-Weave/archives/621137">Game8 — is there romance?</a></li>
<li><a href="https://game8.co/games/Fire-Emblem-Fortunes-Weave/archives/621007">Game8 — how to increase support level</a></li>
<li><a href="https://game8.co/games/Fire-Emblem-Fortunes-Weave/archives/623690">Game8 — gift giving guide</a></li>
<li><a href="https://game8.co/games/Fire-Emblem-Fortunes-Weave/archives/623869">Game8 — Eshmel</a></li>
</ul>
"""
    return page("Supports and Endings", body)


_PAIRING = None


def pairing_cached():
    global _PAIRING
    if _PAIRING is None:
        _PAIRING = best_pairing()
    return _PAIRING


def uses(name):
    """Every build of a unit: (section id, title, build dict, path_n for skill rows)."""
    out = []
    for p in PATHS:
        for b in BUILDS[p["n"]]:
            if b["unit"] == name:
                out.append((f"path-{p['n']}", f"Path {p['n']}: {lord_span(p['lord'])} ({p['difficulty'].split(' · ')[0]})", b, p["n"]))
    for b in PART2["builds"]:
        if b["unit"] == name:
            out.append(("part-2", f"Part II on {lord_span(PART2['route'])} (Hard)", {**b, "join": "Part II"}, 4))
    for sq in PART3:
        for u in sq["units"]:
            if u["unit"] == name:
                out.append(("part-3", f"Part III: Squad {escape(sq['squad'])} (Hard)", part3_build(u, sq["squad"]), "III"))
    return out


def ending_for(name):
    pairing, squad, paths, has_ending = pairing_cached()
    chosen = {frozenset(e[:2]) for e in pairing}
    for a, b, sc, rom in pairing:
        if name in (a, b):
            partner = b if a == name else a
            rivals = sorted({(e2 if e1 == name else e1) for e1, e2, _ in ENDINGS if name in (e1, e2)
                             and frozenset((e1, e2)) not in chosen and "Eshmel" not in (e1, e2)})
            kind = "Eshmel's pick (Support Level 5)" if "Eshmel" in (a, b) else ("romantic" if rom else "platonic or vague")
            txt = f"{char_link(partner, '../')} — {kind} ending. Reach A support and watch the conversation."
            if rivals:
                txt += f" Keep it above {', '.join(char_link(r, '../') for r in rivals)}, who also have an ending with {escape(name)}."
            return txt
    if name in has_ending:
        return "Their only listed ending partner is Eshmel, who is paired elsewhere in this plan. See the Supports page to swap."
    return "No paired ending is listed on Game8 yet."


def render_character(name):
    tier, cn, abil, boons, banes = UNITS[name]
    up = "../../"
    gp = GIFT_PREFS.get(name, {})
    home = home_lord(name)
    u_list = uses(name)
    used = ", ".join(f'<a href="#{sid}">{re.sub(r"<[^>]+>", "", t).split(" (")[0]}</a>' for sid, t, _, _ in u_list)
    growth_row = "".join(f"<td>{v}</td>" for v in UNIT_GROWTH[name])
    head = "".join(f"<th>{k}</th>" for k in STATS)
    recruit = ""
    for n, rows in RECRUIT.items():
        for r in rows:
            if r[0] == name:
                u, a, s_, rn, item, how, ch = r
                recruit += (f"<tr><td>Path {n} ({LORDS[PATHS[n - 1]['lord']]['name']})</td><td>{a}</td><td>{s_}</td>"
                            f"<td>{rn}</td><td>{escape(item)}</td><td>{escape(how)}</td><td><b>{ch}</b></td></tr>")
    recruit_html = (f'<h2>Recruiting</h2><div class="table-wrap"><table><tr><th>Path</th><th>Appears</th><th>Support</th>'
                    f'<th>Renown</th><th>Item or task</th><th>Where / how</th><th>Recruit in</th></tr>{recruit}</table></div>'
                    if recruit else "")
    builds = ""
    for sid, title, b, pn in u_list:
        builds += f'<section class="card" id="{sid}"><h2>{title}{copy_tag(b)}</h2>{build_details(b, pn)}</section>'
    profile = [("Chinese name", cn), ("Game8 tier", tier), ("Used in", used),
               ("Personal abilities", escape(abil)), ("Boons", escape(boons)), ("Banes", escape(banes)),
               ("Likes", escape(gp.get("likes", ""))), ("Interests", escape(gp.get("interests", "")))]
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in profile if v)
    gifts = ""
    if gp.get("loved") or gp.get("liked"):
        gifts = "<h2>Gifts they like</h2><dl class=\"gifts\">"
        if gp.get("loved"):
            gifts += f"<dt>Loved</dt><dd>{escape(gp['loved'])}</dd>"
        if gp.get("liked"):
            gifts += f"<dt>Really liked</dt><dd>{escape(gp['liked'])}</dd>"
        gifts += ("</dl><p class=\"meta\">Loved gifts give the most support; a gift on their birthday always gets the best reaction "
                  "(Game8 gift guide).</p>")
    else:
        gifts = "<h2>Gifts they like</h2><p>Game8's gift guide lists no gift preferences for this character.</p>"
    body = f"""
<div class="card-head">{avatar(name, up, large=True)}<div>
<h1>{escape(name)}</h1>
<p class="meta">{cn} · Game8 tier {tier}{f" · first used on {lord_span(home)}'s path" if home else ""}</p>
</div></div>
<dl class="profile">{dl}</dl>
<h2>Growth rates</h2>
<div class="table-wrap"><table><tr>{head}</tr><tr>{growth_row}</tr></table></div>
<p class="meta">Character growths (Keengamer); add the class modifier from the <a href="../skills.html">Skills page</a>.</p>
{gifts}
<h2>Paired ending</h2>
<p>{ending_for(name)}</p>
{recruit_html}
<h2>Builds</h2>
{builds or "<p>Not used in this plan.</p>"}
"""
    return page(f"{name} — Fortune's Weave build", body, depth=2)


def render_characters_index():
    groups = [("Lords", [n for n in ("Cai", "Dietrich", "Theodora", "Leda", "Eshmel")])]
    seen = {n for _, ns in groups for n in ns}
    for p in PATHS:
        ns = [b["unit"] for b in BUILDS[p["n"]] if b["unit"] not in seen and home_lord(b["unit"]) == p["lord"]]
        seen |= set(ns)
        groups.append((f"First used on Path {p['n']}: {lord_span(p['lord'])}", ns))
    groups.append(("Part II and Part III joiners", [n for n in UNITS if n not in seen]))
    body = "<h1>Characters</h1><p class=\"meta\">Every unit in the plan, with all of their builds, growths, gifts and paired ending on one page.</p>"
    for title, ns in groups:
        cards = ""
        for n in ns:
            bits = [re.sub(r"<[^>]+>", "", t).split(":")[0] for _, t, _, _ in uses(n)]
            cards += mini_card(n, " · ".join(dict.fromkeys(bits)), f"{slug(n)}.html", "../../")
        body += f"<h2>{title}</h2><div class=\"cards compact\">{cards}</div>"
    return page("Characters", body, depth=2)


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
        urows += f"<tr><td>{char_link(name)}</td><td>{UNITS[name][0]}</td>{cols}</tr>"

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
        reuse_rows += f"<tr><td>{char_link(u)}</td><td>{'<br>'.join(cells)}</td></tr>"

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
<li>Each build card now shows where to <b>level</b> (growths per class), which masteries to <b>keep</b>, which to <b>farm only</b>, and an <b>equip order</b>. Full mastery and growth tables: <a href="skills.html">Masteries and growth rates</a>.</li>
</ul>

<h2>Supports and endings</h2>
<p>No marriage or S supports, but paired endings exist. The generator picks the largest set of pairs from Game8's list (no unit used twice), preferring partners who fight side by side: see <a href="supports.html">Supports and paired endings</a>.</p>

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
    for n, rows in RECRUIT.items():
        lord = LORDS[PATHS[n - 1]["lord"]]["name"]
        planned = {b["unit"] for b in BUILDS[n]} - {lord}
        listed = {r[0] for r in rows}
        if planned != listed:
            print(f"walkthrough {n} mismatch: missing {sorted(planned - listed)}, extra {sorted(listed - planned)}")
    sizes = [len(sq["units"]) for sq in PART3]
    return missing_units, missing_classes, sizes


def main():
    OUT.mkdir(exist_ok=True)
    missing_units, missing_classes, sizes = check()
    (OUT / "index.html").write_text(render_index())
    for p in PATHS:
        (OUT / f"{p['slug']}.html").write_text(render_path(p))
    (OUT / "part-2-3.html").write_text(render_part23())
    (OUT / "skills.html").write_text(render_skills())
    (OUT / "supports.html").write_text(render_supports())
    CHARS.mkdir(exist_ok=True)
    for name in UNITS:
        (CHARS / f"{slug(name)}.html").write_text(render_character(name))
    (CHARS / "index.html").write_text(render_characters_index())
    sync_static_navs()
    print("missing units:", missing_units)
    print("missing classes:", missing_classes)
    print("squad sizes:", sizes)


if __name__ == "__main__":
    main()

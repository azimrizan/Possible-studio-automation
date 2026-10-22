"""
Turns the director's decision (word ids) into frame-exact render props.

Rules applied here, not by the model:
- cuts always land on word boundaries, with a little padding so consonants aren't clipped;
- pauses longer than MAX_GAP_S are tightened (the gap is removed, padding kept);
- clips shorter than MIN_CLIP_S are dropped to avoid flashes;
- zoom alternates across cuts so a jump cut never looks like a skip;
- beats are clamped to 1.5-8 s, never overlap, and wait for the hook text to finish (except backtext);
- push-ins are at least 3 s apart and only on the speaker (not during graphics);
- sound effects follow the beats (whoosh on layout changes, pops on items, ticks on counters, keys on typing).
"""
from typing import Any, Dict, List, Optional, Set

FPS = 30
PAD_IN_S, PAD_OUT_S = 0.06, 0.12
MAX_GAP_S = 0.35
MIN_CLIP_S = 0.25
HOOK_TEXT_MAX_S = 3.0
BEAT_MIN_F, BEAT_MAX_F = 45, 240
PUNCH_GAP_F = 90
ZOOMS = (1.0, 1.07)
DEFAULT_ACCENT = "#F5C451"


def _f(seconds: float) -> int:
    return int(round(seconds * FPS))


def keep_ranges(words: List[Dict[str, Any]], removed: Set[str], duration: float) -> List[Dict[str, Any]]:
    """Group kept words into continuous ranges; a cut word or a long pause starts a new range."""
    ranges: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    prev_end = None
    for w in words:
        if w["id"] in removed:
            current = None
            prev_end = None
            continue
        if current is None or prev_end is None or w["start"] - prev_end > MAX_GAP_S:
            current = {"start": max(0.0, w["start"] - PAD_IN_S), "end": w["end"], "words": []}
            ranges.append(current)
        current["end"] = min(duration, w["end"] + PAD_OUT_S)
        current["words"].append(w)
        prev_end = w["end"]
    # Neighbouring ranges whose padding overlaps are merged so nothing plays twice.
    merged: List[Dict[str, Any]] = []
    for r in ranges:
        if merged and r["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = r["end"]
            merged[-1]["words"].extend(r["words"])
        else:
            merged.append(r)
    return [r for r in merged if r["end"] - r["start"] >= MIN_CLIP_S]


def _resolver(source_words: List[Dict[str, Any]], out_words: Dict[str, Dict[str, Any]]):
    """Word id -> its output word; a cut word resolves to the next kept word (or the previous one at the end)."""
    order = [w["id"] for w in source_words]
    index = {wid: i for i, wid in enumerate(order)}

    def resolve(wid: str, forward: bool = True) -> Optional[Dict[str, Any]]:
        if wid not in index:
            return None
        i = index[wid]
        steps = list(range(i, len(order))) + list(range(i - 1, -1, -1)) if forward else \
            list(range(i, -1, -1)) + list(range(i + 1, len(order)))
        for j in steps:
            if order[j] in out_words:
                return out_words[order[j]]
        return None

    return resolve


def _beats(plan: Dict[str, Any], resolve, hook_end: int, total: int) -> List[Dict[str, Any]]:
    out = []
    for b in plan.get("beats") or []:
        start_w, end_w = resolve(b.get("start_word_id", "")), resolve(b.get("end_word_id", ""), forward=False)
        if not start_w or not end_w:
            continue
        start, end = start_w["startFrame"], max(end_w["endFrame"] + 6, start_w["startFrame"])
        if b["type"] != "backtext":
            start = max(start, hook_end)
        end = min(total, max(end, start + BEAT_MIN_F), start + BEAT_MAX_F)
        if end - start < BEAT_MIN_F:
            continue
        items = []
        for k, it in enumerate((b.get("items") or [])[:4]):
            w = resolve(it.get("at_word_id", ""))
            frame = w["startFrame"] if w else start + 8 + k * 15
            items.append({"text": it.get("text", ""), "frame": min(max(frame, start + 4), end - 10)})
        out.append({
            "type": b["type"], "startFrame": start, "endFrame": end,
            "text": b.get("text", ""), "sub": b.get("sub", ""), "value": float(b.get("value") or 0),
            "prefix": b.get("prefix", ""), "suffix": b.get("suffix", ""), "items": items, "keyword": b.get("keyword", ""),
        })
    out.sort(key=lambda x: x["startFrame"])
    kept: List[Dict[str, Any]] = []
    for b in out:  # never overlapping: an earlier beat wins
        if kept and b["startFrame"] < kept[-1]["endFrame"]:
            continue
        kept.append(b)
    return kept


def _punches(plan: Dict[str, Any], words: Dict[str, Dict[str, Any]], beats: List[Dict[str, Any]], hook_end: int) -> List[Dict[str, Any]]:
    punches, last = [], -PUNCH_GAP_F
    for wid in plan.get("punch_word_ids") or []:
        w = words.get(wid)
        if not w:
            continue
        f = w["startFrame"]
        if f < hook_end or f - last < PUNCH_GAP_F or any(b["startFrame"] - 6 <= f <= b["endFrame"] for b in beats):
            continue
        punches.append({"startFrame": max(0, f - 3), "endFrame": f + 15})
        last = f
    return sorted(punches, key=lambda p: p["startFrame"])


def _sfx(beats: List[Dict[str, Any]], has_hook_text: bool) -> List[Dict[str, Any]]:
    ev: List[Dict[str, Any]] = []
    if has_hook_text:
        ev.append({"frame": 1, "kind": "hit", "db": -24})
    for b in beats:
        s, e = b["startFrame"], b["endFrame"]
        ev.append({"frame": max(0, s - 6), "kind": "air", "db": -32})
        if b["type"] != "backtext":
            ev.append({"frame": max(0, e - 6), "kind": "air", "db": -35})
        if b["type"] == "statement_card":
            ev.append({"frame": s + 8, "kind": "pop", "db": -30})
        elif b["type"] == "list":
            ev.extend({"frame": it["frame"], "kind": "pop", "db": -30} for it in b["items"])
        elif b["type"] == "counter":
            ev.append({"frame": s + 9, "kind": "ticks", "db": -34, "frames": 18})
        elif b["type"] == "cta_comment":
            ev.extend({"frame": s + 12 + 3 * i, "kind": "key", "db": -33} for i in range(len(b["keyword"])))
        elif b["type"] == "before_after":
            ev.append({"frame": s + 24, "kind": "air", "db": -33})
    return sorted(ev, key=lambda x: x["frame"])


def build_variants(sources: Dict[str, Dict[str, Any]], plan: Dict[str, Any], style: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    style = style or {}
    all_ids = {w["id"] for s in sources.values() for w in s["words"]}
    removed = set(plan.get("remove_word_ids") or []) & all_ids
    emphasis = set(plan.get("emphasis_word_ids") or []) & all_ids
    fixes = {c["word_id"]: c["text"].strip() for c in plan.get("corrections") or [] if c.get("text", "").strip()}
    ranges = {name: keep_ranges(s["words"], removed, s["duration"]) for name, s in sources.items()}

    hooks = [h for h in plan.get("hooks") or [] if h.get("source") in sources][:3]
    if not hooks:
        hooks = [{"source": "main", "overlay_text": "", "accent_words": []}]

    variants = []
    for i, hook in enumerate(hooks):
        order = ["main"] if hook["source"] == "main" else [hook["source"], "main"]
        clips, words, cursor, hook_end = [], [], 0, 0
        for name in order:
            for r in ranges[name]:
                start_f, end_f = _f(r["start"]), _f(r["end"])
                if end_f <= start_f:
                    continue
                clips.append({"src": sources[name]["file"], "startFrame": start_f, "endFrame": end_f, "from": cursor,
                              "zoom": ZOOMS[len(clips) % 2]})
                for w in r["words"]:
                    words.append({
                        "id": w["id"], "text": fixes.get(w["id"], w["text"]), "emphasis": w["id"] in emphasis,
                        "startFrame": cursor + max(0, _f(w["start"]) - start_f),
                        "endFrame": cursor + max(1, _f(w["end"]) - start_f),
                    })
                cursor += end_f - start_f
            if name != "main" and hook["source"] == name:
                hook_end = cursor
        if cursor == 0:
            continue
        if not hook_end:  # text-only hook on the main take, or a hook take that was cut away entirely
            hook_end = min(cursor, _f(HOOK_TEXT_MAX_S))
        hook_text = hook.get("overlay_text", "")
        if not hook_text and hook["source"] == "main":
            hook_end = 0

        by_id = {w["id"]: w for w in words}
        resolve = _resolver(sources["main"]["words"], {k: v for k, v in by_id.items() if k.startswith("main:")})
        beats = _beats(plan, resolve, hook_end if hook_text else 0, cursor)
        title = None
        tid = plan.get("title_at_word_id")
        if plan.get("title_text") and tid and tid in by_id:
            at = by_id[tid]
            if not any(b["startFrame"] <= at["startFrame"] < b["endFrame"] for b in beats):
                title = {"text": plan["title_text"], "startFrame": at["startFrame"], "endFrame": min(cursor, at["startFrame"] + _f(2.5))}

        variants.append({
            "index": i,
            "label": f"Hook {i + 1}",
            "props": {
                "fps": FPS, "width": 1080, "height": 1920, "durationInFrames": cursor,
                "clips": clips, "words": words,
                "hook": {"text": hook_text, "accentWords": hook.get("accent_words") or [], "endFrame": hook_end},
                "title": title,
                "subtitlePosition": plan.get("subtitle_position", "lower"),
                "beats": beats,
                "punches": _punches(plan, by_id, beats, hook_end if hook_text else 0),
                "grade": plan.get("grade", "natural"),
                "accent": style.get("accent") or DEFAULT_ACCENT,
                "sfx": None,  # filled in at render time once the sound file exists
                "masks": [],  # filled in at render time: [{src, frames:[...]}] cut-outs that exist
            },
            "sfx_events": _sfx(beats, bool(hook_text)),
            "duration_s": round(cursor / FPS, 2),
        })
    return variants


def mask_requests(variant: Dict[str, Any]) -> Dict[str, Set[int]]:
    """Source frames that need a person cut-out (backtext beats), per source file."""
    need: Dict[str, Set[int]] = {}
    props = variant["props"]
    for b in props["beats"]:
        if b["type"] != "backtext":
            continue
        for c in props["clips"]:
            lo, hi = max(b["startFrame"], c["from"]), min(b["endFrame"], c["from"] + c["endFrame"] - c["startFrame"])
            for f in range(lo, hi):
                need.setdefault(c["src"], set()).add(c["startFrame"] + f - c["from"])
    return need

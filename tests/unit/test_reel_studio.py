"""AI Video Edit: the timeline rules that turn the director's word choices into frame-exact cuts."""
import pytest

from reel_studio import build_variants, director_mode, plan_edit
from reel_studio.timeline import FPS, keep_ranges


def _words(prefix, spans):
    return [{"id": f"{prefix}:{i}", "text": f"w{i}", "start": s, "end": e} for i, (s, e) in enumerate(spans)]


def _source(prefix, spans, duration):
    return {"file": f"{prefix}.mp4", "duration": duration, "language": "en", "words": _words(prefix, spans)}


def test_long_pause_is_cut_and_short_pause_kept():
    words = _words("main", [(0.5, 0.9), (1.0, 1.4), (3.0, 3.4)])  # 0.1s gap kept, 1.6s gap cut
    ranges = keep_ranges(words, set(), duration=4.0)
    assert len(ranges) == 2
    assert [w["id"] for w in ranges[0]["words"]] == ["main:0", "main:1"]
    assert ranges[0]["start"] == pytest.approx(0.44)  # padded before the first word
    assert ranges[1]["start"] == pytest.approx(2.94)


def test_removed_word_splits_the_range_and_is_never_played():
    words = _words("main", [(0.0, 0.3), (0.35, 0.7), (0.75, 1.1)])
    ranges = keep_ranges(words, {"main:1"}, duration=2.0)
    played = [w["id"] for r in ranges for w in r["words"]]
    assert "main:1" not in played
    # Padding must not reach back into the cut word: ranges never overlap.
    for a, b in zip(ranges, ranges[1:]):
        assert a["end"] <= b["start"]


def test_flash_clips_are_dropped():
    words = _words("main", [(0.0, 1.0), (2.0, 2.05)])  # second word alone would be a 0.17s flash... padded
    ranges = keep_ranges(words, set(), duration=3.0)
    assert all(r["end"] - r["start"] >= 0.25 for r in ranges)


def test_hook_take_plays_first_then_main_with_continuous_timeline():
    sources = {"main": _source("main", [(0.0, 1.0), (1.1, 2.0)], 2.5), "hook1": _source("hook1", [(0.2, 1.5)], 2.0)}
    plan = {"remove_word_ids": [], "emphasis_word_ids": ["main:1"],
            "hooks": [{"source": "hook1", "overlay_text": "stop scrolling", "accent_words": ["stop"]}]}
    [v] = build_variants(sources, plan)
    clips = v["props"]["clips"]
    assert [c["src"] for c in clips] == ["hook1.mp4", "main.mp4"]
    # Each clip starts where the previous one ended.
    assert clips[1]["from"] == clips[0]["endFrame"] - clips[0]["startFrame"]
    assert v["props"]["durationInFrames"] == sum(c["endFrame"] - c["startFrame"] for c in clips)
    # Hook text covers exactly the hook take.
    assert v["props"]["hook"]["endFrame"] == clips[1]["from"]
    assert [w["id"] for w in v["props"]["words"] if w["emphasis"]] == ["main:1"]


def test_text_hooks_on_main_make_one_variant_each_and_unknown_ids_are_ignored():
    sources = {"main": _source("main", [(0.0, 1.0), (1.1, 4.0)], 4.5)}
    plan = {"remove_word_ids": ["main:99", "nope"], "emphasis_word_ids": [],
            "hooks": [{"source": "main", "overlay_text": t, "accent_words": []} for t in ("a", "b", "c")]
            + [{"source": "hook2", "overlay_text": "missing take", "accent_words": []}],
            "title_text": "CLAUDE", "title_at_word_id": "main:1"}
    variants = build_variants(sources, plan)
    assert [v["props"]["hook"]["text"] for v in variants] == ["a", "b", "c"]
    v = variants[0]
    assert v["props"]["hook"]["endFrame"] == 3 * FPS  # text hook capped at 3s on a longer take
    word1 = next(w for w in v["props"]["words"] if w["id"] == "main:1")
    assert v["props"]["title"]["startFrame"] == word1["startFrame"]


@pytest.mark.asyncio
async def test_demo_director_without_key():
    assert director_mode() == "demo"  # conftest blanks ANTHROPIC_API_KEY
    sources = {"main": _source("main", [(i * 0.5, i * 0.5 + 0.4) for i in range(16)], 8.0)}
    plan = await plan_edit(sources, [], "")
    assert plan["mode"] == "demo" and plan["remove_word_ids"] == []
    assert len(plan["hooks"]) == 3 and all(h["source"] == "main" for h in plan["hooks"])


def _beat(type_, start, end, **kw):
    base = {"type": type_, "start_word_id": start, "end_word_id": end, "text": "x", "sub": "", "value": 0,
            "prefix": "", "suffix": "", "items": [], "keyword": ""}
    return {**base, **kw}


def test_beats_land_on_words_never_overlap_and_wait_for_hook_text():
    spans = [(i * 0.5, i * 0.5 + 0.4) for i in range(40)]  # 20 s of steady speech
    sources = {"main": _source("main", spans, 20.5)}
    plan = {"remove_word_ids": ["main:12"], "emphasis_word_ids": [],
            "hooks": [{"source": "main", "overlay_text": "hook", "accent_words": []}],
            "beats": [
                _beat("statement_card", "main:1", "main:3"),         # inside the 3 s hook text: pushed after it
                _beat("list", "main:12", "main:20", items=[{"text": "a", "at_word_id": "main:14"}]),  # starts on a cut word
                _beat("counter", "main:15", "main:18", value=80),     # overlaps the list: dropped
                _beat("backtext", "main:0", "main:4"),                # backtext may sit under the hook text
            ]}
    [v] = build_variants(sources, plan)
    beats = v["props"]["beats"]
    words = {w["id"]: w for w in v["props"]["words"]}
    types = [b["type"] for b in beats]
    assert "counter" not in types
    card = next(b for b in beats if b["type"] == "statement_card")
    assert card["startFrame"] >= v["props"]["hook"]["endFrame"]
    lst = next(b for b in beats if b["type"] == "list")
    assert lst["startFrame"] == words["main:13"]["startFrame"]  # cut word resolves to the next kept word
    assert lst["items"][0]["frame"] == words["main:14"]["startFrame"]
    ordered = sorted(beats, key=lambda b: b["startFrame"])
    non_back = [b for b in ordered if b["type"] != "backtext"]
    for a, b in zip(non_back, non_back[1:]):
        assert a["endFrame"] <= b["startFrame"]
    assert all(45 <= b["endFrame"] - b["startFrame"] <= 240 for b in beats)


def test_zoom_alternates_and_sound_follows_beats():
    sources = {"main": _source("main", [(0.0, 1.0), (2.0, 3.0), (4.0, 5.0), (5.1, 9.0)], 9.5)}
    plan = {"remove_word_ids": [], "emphasis_word_ids": [], "hooks": [{"source": "main", "overlay_text": "h", "accent_words": []}],
            "beats": [_beat("list", "main:3", "main:3", items=[{"text": "a", "at_word_id": "main:3"}])]}
    [v] = build_variants(sources, plan)
    assert [c["zoom"] for c in v["props"]["clips"]] == [1.0, 1.07, 1.0]
    kinds = [e["kind"] for e in v["sfx_events"]]
    assert kinds[0] == "hit" and "pop" in kinds and "air" in kinds


def test_corrections_change_caption_text_only():
    sources = {"main": _source("main", [(0.0, 0.4), (0.5, 0.9)], 1.5)}
    plan = {"remove_word_ids": [], "emphasis_word_ids": [], "hooks": [],
            "corrections": [{"word_id": "main:1", "text": "Claude"}, {"word_id": "main:0", "text": "  "}]}
    [v] = build_variants(sources, plan)
    assert [w["text"] for w in v["props"]["words"]] == ["w0", "Claude"]

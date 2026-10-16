import io

import pytest
from PIL import Image

from poster_studio import PosterPipeline, PosterRequest, RegenerateRequest, StoreError, StudioStore
from poster_studio.composer import compose_prompt
from poster_studio.schemas import DesignConcept, LogoProfile, ProductProfile, QAResult

WS = "workspace-test-01"


def _png(color=(200, 30, 40), size=(64, 80), mode="RGB") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, "PNG")
    return buf.getvalue()


def _concept(**overrides) -> DesignConcept:
    data = dict(
        name="Festive Glow",
        big_idea="A lantern lit by the product",
        scene="Red paper lantern with the air fryer glowing inside, marigolds around",
        composition="hero_center",
        camera="85mm_eye_level",
        lighting="backlit_glow",
        colour_strategy="brand_led",
        palette=["#e11d48", "#111827", "#fbbf24"],
        type_style="editorial_serif",
        text_zone="upper_third",
        logo_zone="top_right",
        headline="Light Up Healthy",
        subline="20% off this Diwali",
        cta="Shop now",
        mood=["warm", "festive", "premium"],
        caption="Crisp festive snacks with less oil.",
        hashtags=["#Diwali"],
        alt="Air fryer inside a glowing lantern",
    )
    data.update(overrides)
    return DesignConcept(**data)


class FakeAgents:
    """Stands in for the Groq agents: no network, deterministic output, records calls."""

    def __init__(self, qa_results=None):
        self.qa_results = list(qa_results or [])
        self.calls = []

    async def analyse_product(self, image):
        self.calls.append("product")
        return ProductProfile(category="air fryer", description="black 5L air fryer", must_preserve=["digital dial"]), {"prompt_tokens": 10, "completion_tokens": 5}

    async def analyse_logo(self, logo):
        return LogoProfile(kind="wordmark", reads_as="CRISPO", best_on="light"), {"prompt_tokens": 5, "completion_tokens": 3}

    @staticmethod
    def build_director_input(*args):
        from poster_studio.agents import PosterAgents
        return PosterAgents.build_director_input(*args)

    async def direct(self, director_input):
        self.calls.append(("direct", director_input))
        return [_concept(name=f"C{i}", headline=f"Headline {i}") for i in range(1, 4)], {"prompt_tokens": 100, "completion_tokens": 50}

    async def revise(self, concept, change):
        self.calls.append(("revise", change))
        return concept.model_copy(update={"headline": "Revised Headline"}), {"prompt_tokens": 20, "completion_tokens": 10}

    async def inspect(self, poster, headline, logo):
        self.calls.append("qa")
        result = self.qa_results.pop(0) if self.qa_results else QAResult()
        return result, {"prompt_tokens": 30, "completion_tokens": 4}


class FakeImages:
    def __init__(self):
        self.calls = []

    async def __call__(self, prompt, refs, aspect_ratio):
        self.calls.append((prompt, [m for _, m in refs], aspect_ratio))
        return _png(size=(80, 100)), "image/png", "fake-image-model"


@pytest.fixture
def store(tmp_path):
    return StudioStore(root=tmp_path)


def test_concept_normalised_clamps_unknown_enums():
    c = _concept(composition="made_up", lighting="nope", palette=["#fff000", "red"]).normalised()
    assert c.composition == "hero_center"
    assert c.lighting == "softbox_commercial"
    assert c.palette == ["#fff000"]


def test_composer_declares_reference_roles_and_exact_text():
    brand = {"brand_name": "Crispo", "logo_profile": {"best_on": "light"}}
    prompt = compose_prompt(_concept(), "4:5", 1, ProductProfile(must_preserve=["digital dial"]), "air fryer", brand, has_logo=True)
    assert "Image 1: the real product" in prompt
    assert "Image 2: the brand logo" in prompt
    assert "top-right corner" in prompt
    assert 'Headline: "Light Up Healthy"' in prompt
    assert "digital dial" in prompt
    # With a real logo supplied, the brand name must not also be rendered as a wordmark.
    assert "Brand wordmark" not in prompt


def test_composer_without_photo_or_logo_uses_brief_and_wordmark():
    prompt = compose_prompt(_concept(), "1:1", 0, None, "Crispo air fryer", {"brand_name": "Crispo"}, has_logo=False)
    assert "REFERENCE IMAGES" not in prompt
    assert "PRODUCT: Crispo air fryer" in prompt
    assert 'Brand wordmark: "Crispo"' in prompt


def test_composer_without_brand_kit_has_no_brand_lines():
    prompt = compose_prompt(_concept(), "4:5", 0, None, "air fryer", {}, has_logo=False)
    assert "wordmark" not in prompt and "brand logo" not in prompt


def test_store_rejects_bad_ids(store):
    with pytest.raises(StoreError):
        store.load_brand_kit("../etc")
    with pytest.raises(StoreError):
        store.read_asset(WS, "../../brand_kit.json")
    with pytest.raises(StoreError):
        store.read_asset(WS, "0" * 32 + ".png")  # well-formed but missing


@pytest.mark.asyncio
async def test_pipeline_without_brand_kit_or_photo(store):
    agents, images = FakeAgents(), FakeImages()
    result = await PosterPipeline(store, agents).generate(WS, PosterRequest(brief={"product_focus": "air fryer"}), images)
    assert [v["status"] for v in result["variants"]] == ["ready"] * 3
    assert all(refs == [] for _, refs, _ in images.calls)
    assert result["brand_kit_applied"] is False
    assert "product" not in agents.calls
    assert result["variants"][0]["bgUrl"].startswith("/api/studio/assets/")


@pytest.mark.asyncio
async def test_pipeline_sends_product_and_logo_and_caches_profile(store):
    product = store.save_asset(WS, _png(), "image/png")
    logo = store.save_asset(WS, _png(mode="RGBA", color=(0, 0, 0, 255)), "image/png")
    store.save_brand_kit(WS, {"brand_name": "Crispo", "colors": ["#e11d48"], "logo": {"asset_id": logo["asset_id"]}})
    agents, images = FakeAgents(), FakeImages()
    pipe = PosterPipeline(store, agents)
    req = PosterRequest(brief={"product_focus": "air fryer"}, user_direction="Diwali 20% off", product_asset_ids=[product["asset_id"]])

    await pipe.generate(WS, req, images)
    assert all(refs == ["image/png", "image/png"] for _, refs, _ in images.calls)
    director_input = next(c[1] for c in agents.calls if isinstance(c, tuple) and c[0] == "direct")
    assert "Diwali 20% off" in director_input and "name=Crispo" in director_input

    await pipe.generate(WS, req, images)
    assert agents.calls.count("product") == 1  # second run served from cache


@pytest.mark.asyncio
async def test_pipeline_qa_retry_then_logo_lock(store):
    logo = store.save_asset(WS, _png(mode="RGBA", color=(0, 0, 0, 255)), "image/png")
    store.save_brand_kit(WS, {"logo": {"asset_id": logo["asset_id"]}, "logo_profile": {"kind": "wordmark", "reads_as": "X"}})
    bad = QAResult(headline_ok=False, logo_ok=False, issue="misspelt headline")
    still_bad_logo = QAResult(headline_ok=True, logo_ok=False, issue="logo warped")
    agents = FakeAgents(qa_results=[bad, still_bad_logo, QAResult(), QAResult()])
    images = FakeImages()
    result = await PosterPipeline(store, agents).generate(WS, PosterRequest(), images)

    first = result["variants"][0]
    assert first["qa"]["retried"] is True and first["qa"]["logo_locked"] is True
    assert len(images.calls) == 4  # 3 renders + 1 retry
    assert any("CORRECTION FROM REVIEW" in p for p, _, _ in images.calls)


@pytest.mark.asyncio
async def test_pipeline_reports_failure_when_every_render_fails(store):
    async def failing(prompt, refs, ar):
        raise RuntimeError("quota exhausted")

    from poster_studio import PipelineError

    with pytest.raises(PipelineError, match="quota exhausted"):
        await PosterPipeline(store, FakeAgents()).generate(WS, PosterRequest(), failing, run_qa=False)


@pytest.mark.asyncio
async def test_regenerate_text_edit_skips_llm_and_change_uses_revise(store):
    agents, images = FakeAgents(), FakeImages()
    pipe = PosterPipeline(store, agents)
    edited = _concept(headline="My Own Headline").model_dump()

    out = await pipe.regenerate(WS, RegenerateRequest(concept=edited, index=2), images, run_qa=False)
    assert out["variant"]["headline"] == "My Own Headline" and out["usage"]["calls"] == 0

    out = await pipe.regenerate(WS, RegenerateRequest(concept=edited, index=2, change="make it moodier"), images, run_qa=False)
    assert out["variant"]["headline"] == "Revised Headline" and out["usage"]["calls"] == 1


@pytest.mark.asyncio
async def test_studio_api_brand_kit_is_optional_and_uploads_work(client, tmp_path, monkeypatch):
    from apps.api.app.api import studio

    monkeypatch.setattr(studio, "store", StudioStore(root=tmp_path))
    monkeypatch.setattr(studio, "agents", FakeAgents())
    monkeypatch.setattr(studio, "pipeline", PosterPipeline(studio.store, studio.agents))
    monkeypatch.setenv("MOCK_GEMINI", "true")
    headers = {"X-Studio-Workspace": WS}

    empty = (await client.get("/api/studio/brand-kit", headers=headers)).json()
    assert empty["logo"] is None and empty["brand_name"] == ""

    kit = (await client.put("/api/studio/brand-kit", headers=headers, json={"brand_name": "Crispo", "colors": ["#e11d48", "bad"]})).json()
    assert kit["colors"] == ["#e11d48"]

    up = await client.post("/api/studio/brand-kit/logo", headers=headers, files={"file": ("logo.png", _png(mode="RGBA"), "image/png")})
    assert up.status_code == 200 and up.json()["logo_profile"]["reads_as"] == "CRISPO"
    asset = await client.get(up.json()["logo"]["url"])
    assert asset.status_code == 200 and asset.headers["content-type"] == "image/png"

    bad = await client.post("/api/studio/uploads", headers=headers, files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 400

    product = (await client.post("/api/studio/uploads", headers=headers, files={"file": ("p.jpg", _png(), "image/png")})).json()
    gen = await client.post(
        "/api/studio/posters/generate",
        headers=headers,
        json={"brief": {"product_focus": "air fryer"}, "product_asset_ids": [product["asset_id"]], "use_brand_kit": False},
    )
    body = gen.json()
    assert gen.status_code == 200 and body["data"]["mock"] is True and len(body["data"]["variants"]) == 3
    assert body["data"]["brand_kit_applied"] is False

    assert (await client.delete("/api/studio/brand-kit/logo", headers=headers)).json()["logo"] is None


@pytest.mark.asyncio
async def test_studio_api_requires_gemini_when_not_mocked(client, monkeypatch):
    monkeypatch.setenv("MOCK_GEMINI", "false")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = await client.post("/api/studio/posters/generate", headers={"X-Studio-Workspace": WS}, json={})
    assert res.status_code == 400 and "Gemini is not connected" in res.json()["detail"]

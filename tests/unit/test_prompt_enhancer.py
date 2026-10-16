import pytest
from prompt_enhancer import PromptEnhancerAgent
from model_gateway import ModelGateway
from mcp_common import TenantContext
from apps.api.app.schemas.schemas import CreativeBriefCreate

EVAL_PROMPTS_SET = [
    # 1. Product launch - Both poster & reel
    "Promote our new AI smartwatch on Instagram. Create a poster and a reel, publish it and run a ₹10,000 ad campaign for 7 days targeting the right audience to drive sales.",
    # 2. Air Fryer Promo
    "Make a digital poster for my new smart air fryer with 85% oil reduction to drive direct kitchenware sales.",
    # 3. Protein Bar awareness
    "Generate brand awareness with a dynamic Instagram reel showcasing vegan protein bars for marathon runners.",
    # 4. Flash sale announcement
    "Announce a 40% off weekend flash sale for our wireless noise-cancelling headphones. Create both feed poster and reel.",
    # 5. SaaS CRM lead gen
    "Generate B2B leads for our real estate automation CRM software targeting commercial brokers in Mumbai.",
    # 6. Coffee subscription
    "Promote our artisanal organic coffee bean monthly subscription. Drive website signups with a free sample CTA.",
    # 7. Ergonomic chair
    "Create an educational reel showing spinal health benefits of our ergonomic office chair for remote tech workers.",
    # 8. Skincare serum
    "Launch our Vitamin C brightening facial serum on Instagram. Create an aesthetic poster focusing on clean ingredients.",
    # 9. Online coding bootcamp
    "Drive course enrollments for our Full Stack AI Bootcamp with 100% placement support. Run ad campaign.",
    # 10. EV scooter pre-orders
    "Promote pre-booking for our Gen-2 electric scooter with 150km range. Poster and reel with ₹999 reserve CTA.",
    # 11. Yoga retreat
    "Promote an early bird discount for our 5-day wellness and yoga retreat in Rishikesh.",
    # 12. Pet nutrition
    "Run an ad campaign targeting new puppy owners with our grain-free probiotic dog food.",
    # 13. Smart home lock
    "Create a reel demonstrating keyless fingerprint security for our smart door lock.",
    # 14. Luxury watch restoration
    "Showcase vintage watch servicing and restoration craftsmanship to attract high-net-worth collectors.",
    # 15. Cloud backup service
    "Promote automated ransomware protection for small businesses to drive free trial starts.",
    # 16. Organic baby clothing
    "Introduce our 100% GOTS certified cotton baby onesies with soft pastel aesthetic.",
    # 17. Fitness gym membership
    "Announce annual gym membership at 50% discount with free personal training assessment.",
    # 18. Designer eyewear
    "Drive footfall to our flagship optical boutique with custom frame fitting consultation CTA.",
    # 19. Gourmet meal prep delivery
    "Highlight chef-curated low-carb meal plans delivered fresh daily in Delhi NCR.",
    # 20. Smart water bottle
    "Showcase hydration tracking and LED reminder ring on our stainless steel smart bottle in a 15s reel.",
]

@pytest.mark.asyncio
async def test_prompt_enhancer_eval_20_prompts():
    """
    Acceptance Criteria: An eval set of 20 prompts yields schema-valid briefs.
    """
    model_gw = ModelGateway(mock_mode=True)
    agent = PromptEnhancerAgent(model_gateway=model_gw)
    tenant_ctx = TenantContext(tenant_id="tenant-eval-123", workspace_role="EDITOR")

    passed_count = 0

    for prompt in EVAL_PROMPTS_SET:
        brief: CreativeBriefCreate = await agent.enhance_prompt(
            raw_prompt=prompt,
            tenant_context=tenant_ctx,
        )

        # Validation assertions
        assert isinstance(brief, CreativeBriefCreate)
        assert len(brief.objective) > 0
        assert len(brief.product_focus) > 0
        assert brief.target_audience is not None
        assert len(brief.target_audience.age_range) > 0
        assert len(brief.target_audience.interests) >= 1
        assert brief.deliverables in ["POSTER", "REEL", "BOTH"]
        assert len(brief.channels) >= 1
        assert len(brief.call_to_action) > 0
        assert len(brief.constraints) >= 1
        assert len(brief.enhanced_prompt) > len(prompt) * 0.5
        assert brief.diff_summary is not None

        passed_count += 1

    assert passed_count == 20

@pytest.mark.asyncio
async def test_prompt_enhancer_checklist_streaming():
    """
    Verifies that the agent emits all 6 steps in the UX flow checklist during generation.
    """
    model_gw = ModelGateway(mock_mode=True)
    agent = PromptEnhancerAgent(model_gateway=model_gw)
    tenant_ctx = TenantContext(tenant_id="tenant-stream-1", workspace_role="EDITOR")

    emitted_steps = []

    async def on_progress(event):
        emitted_steps.append(event["step_id"])

    await agent.enhance_prompt(
        raw_prompt=EVAL_PROMPTS_SET[0],
        tenant_context=tenant_ctx,
        progress_callback=on_progress,
    )

    expected = [
        "understanding_goal",
        "analyzing_product",
        "researching_market",
        "creating_audience",
        "planning_creatives",
        "preparing_campaign",
    ]
    assert emitted_steps == expected

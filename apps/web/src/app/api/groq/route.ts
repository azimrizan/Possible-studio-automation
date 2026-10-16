import { NextRequest, NextResponse } from "next/server";

const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const GROQ_REASONING_MODEL = process.env.GROQ_REASONING_MODEL || "openai/gpt-oss-120b";
const GROQ_FAST_MODEL = process.env.GROQ_FAST_MODEL || "openai/gpt-oss-20b";

async function callGroq(messages: any[], model: string, responseFormatJson: boolean = true) {
  const payload: any = {
    model,
    messages,
    temperature: 0.6,
  };
  if (responseFormatJson) {
    payload.response_format = { type: "json_object" };
  }

  const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GROQ_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Groq API returned ${res.status}: ${errorText}`);
  }

  const data = await res.json();
  const content = data.choices[0]?.message?.content;
  return responseFormatJson ? JSON.parse(content) : content;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action, payload } = body;

    if (action === "enhance_brief") {
      const { raw_prompt, product_details, brand_name, image_ref } = payload;
      const systemPrompt = `You are the Prompt Enhancer & Creative Director Agent for an AI Marketing Platform.
Analyze the user's campaign request and product details.
Synthesize a structured, high-converting Creative Brief adhering to this JSON schema:
{
  "objective": "string (e.g. Drive sales, Generate brand awareness, Drive website traffic)",
  "product_focus": "string (extract clean product/offering title directly from user prompt)",
  "target_audience": {
    "age_range": "string (inferred relevant demographic range e.g. 24-38 years)",
    "location": "string (inferred geographic reach e.g. Top Metros / Global)",
    "interests": ["string array of 3-4 key customer affinity interests"],
    "estimated_reach": "string (e.g. 1.2M - 1.8M people)"
  },
  "tone": "string (e.g. Inspiring, energetic, sophisticated)",
  "deliverables": "BOTH",
  "channels": "Instagram + Meta Ads",
  "call_to_action": "string (e.g. Shop Now, Get Started, Claim Offer)",
  "duration": "string (inferred duration e.g. 7 days)",
  "budget": "string (inferred budget e.g. ₹10,000)",
  "constraints": ["string array of 3 strategic brand guardrails"],
  "enhanced_prompt": "string (expanded comprehensive creative directive)",
  "diff_summary": "string (summary of strategic additions made from raw prompt)"
}`;

      const userPrompt = `Brand Name: ${brand_name || "Possible Studio"}
Raw Campaign Prompt: "${raw_prompt}"
${image_ref ? `Image Reference Attached: ${image_ref}\n` : ""}Product Details: ${JSON.stringify(product_details || {})}`;

      const result = await callGroq(
        [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        GROQ_REASONING_MODEL,
        true
      );

      return NextResponse.json({ success: true, model: GROQ_REASONING_MODEL, data: result });
    }

    if (action === "generate_creatives") {
      const { brief, brand_name, image_ref } = payload;
      const systemPrompt = `You are an elite Graphic Designer & Art Director Agent.
Produce 3 distinct visual & copy concepts for a multi-variant social campaign tailored specifically to the user's prompt.
Variant 1: High Tech / Modern Bold precision
Variant 2: Vibrant Lifestyle Action / Energy
Variant 3: Minimalist Luxury / Modern Elegance

Return ONLY a JSON object matching this schema:
{
  "variants": [
    {
      "index": 1,
      "theme": "dark_titanium",
      "title": "Bold & High-Impact Precision",
      "tag": "V1 · HERO",
      "description": "string (visual art director concept notes)",
      "visual_prompt": "string (detailed commercial product photography prompt for this concept, 8k, photorealistic, studio lighting)",
      "accent": "#6366f1",
      "badge": "NEW LAUNCH",
      "headline": "string (short uppercase punchy headline)",
      "subheadline": "string (compelling 1-sentence value prop)",
      "cta": "string",
      "copy": {
        "hook": "string (opening hook sentence)",
        "body": "string (conversion body copy)",
        "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
        "alt": "string"
      }
    },
    {
      "index": 2,
      "theme": "lifestyle_action",
      "title": "Lifestyle Action / Dynamic Energy",
      "tag": "V2 · LIFESTYLE",
      "description": "string",
      "visual_prompt": "string (lifestyle action photography prompt)",
      "accent": "#f59e0b",
      "badge": "TRENDING NOW",
      "headline": "string (short uppercase punchy headline)",
      "subheadline": "string",
      "cta": "string",
      "copy": {
        "hook": "string",
        "body": "string",
        "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
        "alt": "string"
      }
    },
    {
      "index": 3,
      "theme": "minimalist_luxury",
      "title": "Minimalist Luxury / Elegance",
      "tag": "V3 · LUXURY",
      "description": "string",
      "visual_prompt": "string (minimalist luxury studio photography prompt)",
      "accent": "#10b981",
      "badge": "EXCLUSIVE",
      "headline": "string (short uppercase punchy headline)",
      "subheadline": "string",
      "cta": "string",
      "copy": {
        "hook": "string",
        "body": "string",
        "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
        "alt": "string"
      }
    }
  ]
}`;

      const userPrompt = `Brand: ${brand_name || "Possible Studio"}
Product Focus: ${brief?.product_focus || "Featured Offering"}
Objective: ${brief?.objective || "Drive Sales"}
Tone: ${brief?.tone || "Authoritative and Inspiring"}
CTA: ${brief?.call_to_action || "Shop Now"}
${image_ref ? `Image Reference Provided: ${image_ref}\n` : ""}`;

      const result = await callGroq(
        [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        GROQ_REASONING_MODEL,
        true
      );

      if (result?.variants && Array.isArray(result.variants)) {
        result.variants = result.variants.map((v: any, idx: number) => {
          const resolvedUrl = image_ref || null;
          return {
            ...v,
            bgUrl: resolvedUrl,
          };
        });
      }

      return NextResponse.json({ success: true, model: GROQ_REASONING_MODEL, data: result });
    }

    if (action === "generate_storyboard") {
      const { brief, brand_name, image_ref } = payload;
      const systemPrompt = `You are a viral social video director specializing in high-converting 9:16 vertical reels.
Create a 4-scene structured video storyboard (15s total) tailored to the product:
Scene 1: Hook (3.0s)
Scene 2: Core Feature Reveal (4.0s)
Scene 3: Lifestyle Action / Proof (4.0s)
Scene 4: Outro & Call to Action (4.0s)

Return ONLY a JSON object:
{
  "scenes": [
    {
      "id": 1,
      "title": "The Hook",
      "duration": "3.0s",
      "timecode": "0:00 - 0:03",
      "visual": "string (visual scene description)",
      "bgUrl": null,
      "caption": "string (uppercase kinetic text overlay)",
      "voiceover": "string (spoken script line)",
      "cue": "string (musical or sound effect cue)"
    },
    {
      "id": 2,
      "title": "Core Feature Reveal",
      "duration": "4.0s",
      "timecode": "0:03 - 0:07",
      "visual": "string",
      "bgUrl": null,
      "caption": "string",
      "voiceover": "string",
      "cue": "string"
    },
    {
      "id": 3,
      "title": "Lifestyle Action / Proof",
      "duration": "4.0s",
      "timecode": "0:07 - 0:11",
      "visual": "string",
      "bgUrl": null,
      "caption": "string",
      "voiceover": "string",
      "cue": "string"
    },
    {
      "id": 4,
      "title": "Outro & Call To Action",
      "duration": "4.0s",
      "timecode": "0:11 - 0:15",
      "visual": "string",
      "bgUrl": null,
      "caption": "string",
      "voiceover": "string",
      "cue": "string"
    }
  ]
}`;

      const userPrompt = `Brand: ${brand_name || "Possible Studio"}
Product: ${brief?.product_focus || "Featured Offering"}
CTA: ${brief?.call_to_action || "Shop Now"}
Tone: ${brief?.tone || "Viral & Inspiring"}
${image_ref ? `Image Reference Provided: ${image_ref}\n` : ""}`;

      const result = await callGroq(
        [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        GROQ_REASONING_MODEL,
        true
      );

      if (result?.scenes && Array.isArray(result.scenes)) {
        result.scenes = result.scenes.map((s: any, idx: number) => {
          const resolvedUrl = image_ref || null;
          return {
            ...s,
            bgUrl: resolvedUrl,
          };
        });
      }

      return NextResponse.json({ success: true, model: GROQ_REASONING_MODEL, data: result });
    }

    if (action === "review_targeted_regeneration") {
      const { feedback, target_deliverable, current_headline, current_cta } = payload;
      const systemPrompt = `You are a targeted creative revision AI assistant.
Convert reviewer free-text feedback into targeted updates for the selected creative deliverable.
Return ONLY a JSON object:
{
  "updated_headline": "string (refined punchy headline)",
  "updated_subheadline": "string",
  "updated_cta": "string",
  "updated_accent": "string (hex code, e.g. #a855f7)",
  "diff_summary": "string (concise summary of exact modifications made)"
}`;

      const userPrompt = `Reviewer Feedback: "${feedback}"
Target Deliverable: "${target_deliverable}"
Current Headline: "${current_headline}"
Current CTA: "${current_cta}"`;

      const result = await callGroq(
        [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        GROQ_FAST_MODEL,
        true
      );

      return NextResponse.json({ success: true, model: GROQ_FAST_MODEL, data: result });
    }

    return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
  } catch (err: any) {
    console.error("Groq API handler error:", err);
    return NextResponse.json({ error: err.message || "Failed processing Groq request" }, { status: 500 });
  }
}

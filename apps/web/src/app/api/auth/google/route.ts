import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

// GET /api/auth/google — Initiates the Google OAuth2 flow
export async function GET(req: NextRequest) {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

  if (!clientId) {
    return NextResponse.json(
      { error: "GOOGLE_CLIENT_ID is not configured in .env.local" },
      { status: 500 }
    );
  }

  // Generate a CSRF state token and store it in a cookie
  const state = crypto.randomBytes(16).toString("hex");

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: `${appUrl}/api/auth/google/callback`,
    response_type: "code",
    scope: [
      "openid",
      "email",
      "profile",
      // Gemini API with user OAuth: cloud-platform authorises generateContent;
      // there is no bare ".../auth/generative-language" scope (Google returns invalid_scope).
      "https://www.googleapis.com/auth/cloud-platform",
      "https://www.googleapis.com/auth/generative-language.retriever",
    ].join(" "),
    access_type: "offline",
    prompt: "consent select_account",
    state,
  });

  const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;

  const response = NextResponse.redirect(googleAuthUrl);

  // Store state in an HTTP-only cookie for CSRF verification on callback
  response.cookies.set("google_oauth_state", state, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 10, // 10 minutes
    path: "/",
  });

  return response;
}

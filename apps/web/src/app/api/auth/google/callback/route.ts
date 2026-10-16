import { NextRequest, NextResponse } from "next/server";

// GET /api/auth/google/callback — Google redirects here after user approves
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

  // Handle user denial
  if (error) {
    console.error("[OAuth Callback] Google denied access:", error);
    return NextResponse.redirect(
      `${appUrl}?oauth_error=${encodeURIComponent(error)}`
    );
  }

  if (!code) {
    return NextResponse.redirect(
      `${appUrl}?oauth_error=missing_code`
    );
  }

  // CSRF state verification
  const savedState = req.cookies.get("google_oauth_state")?.value;
  if (!savedState || savedState !== state) {
    console.error("[OAuth Callback] CSRF state mismatch");
    return NextResponse.redirect(`${appUrl}?oauth_error=state_mismatch`);
  }

  try {
    // Exchange authorization code for access token
    const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code,
        client_id: process.env.GOOGLE_CLIENT_ID!,
        client_secret: process.env.GOOGLE_CLIENT_SECRET!,
        redirect_uri: `${appUrl}/api/auth/google/callback`,
        grant_type: "authorization_code",
      }).toString(),
    });

    if (!tokenRes.ok) {
      const errBody = await tokenRes.text();
      console.error("[OAuth Callback] Token exchange failed. Status:", tokenRes.status);
      console.error("[OAuth Callback] Error body:", errBody);
      console.error("[OAuth Callback] redirect_uri used:", `${appUrl}/api/auth/google/callback`);
      console.error("[OAuth Callback] client_id used:", process.env.GOOGLE_CLIENT_ID);

      // Parse error details for better user feedback
      let errDetail = "token_exchange_failed";
      try {
        const errJson = JSON.parse(errBody);
        errDetail = errJson.error_description || errJson.error || errDetail;
      } catch {}
      return NextResponse.redirect(
        `${appUrl}?oauth_error=${encodeURIComponent(errDetail)}`
      );
    }

    const tokenData = await tokenRes.json();
    const accessToken: string = tokenData.access_token;
    const refreshToken: string | undefined = tokenData.refresh_token;

    // Fetch user profile using the access token
    const profileRes = await fetch(
      "https://www.googleapis.com/oauth2/v2/userinfo",
      {
        headers: { Authorization: `Bearer ${accessToken}` },
      }
    );

    if (!profileRes.ok) {
      return NextResponse.redirect(`${appUrl}?oauth_error=profile_fetch_failed`);
    }

    const profile = await profileRes.json();

    // Build the session payload
    const sessionPayload = {
      name: profile.name || "Google User",
      email: profile.email || "",
      avatar: profile.picture || `https://api.dicebear.com/7.x/identicon/svg?seed=${encodeURIComponent(profile.email || "user")}`,
      access_token: accessToken,
      refresh_token: refreshToken || null,
      scopes: ["openid", "email", "profile", "gemini.inference", "imagen.generate"],
      connected_at: new Date().toISOString(),
      expires_in: tokenData.expires_in || 3600,
    };

    // Redirect back to the app with session info encoded in URL (stored to localStorage by frontend)
    const redirectUrl = new URL(appUrl);
    redirectUrl.searchParams.set("oauth_success", "1");
    redirectUrl.searchParams.set("session", Buffer.from(JSON.stringify(sessionPayload)).toString("base64"));

    const response = NextResponse.redirect(redirectUrl.toString());

    // Clear the state cookie
    response.cookies.delete("google_oauth_state");

    return response;
  } catch (err: any) {
    console.error("[OAuth Callback] Unexpected error:", err);
    return NextResponse.redirect(`${appUrl}?oauth_error=server_error`);
  }
}

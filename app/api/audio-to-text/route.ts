import { NextRequest, NextResponse } from "next/server";

// ✅ Replace with your actual Ngrok URL
const LOCAL_STT_API = "https://66d0-116-15-163-188.ngrok-free.app/transcribe";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { audio } = body;

    if (!audio) {
      return NextResponse.json({ error: "No audio file provided" }, { status: 400 });
    }

    console.log("📤 Sending audio to local STT API...");

    // ✅ Send audio to local API (via Ngrok)
    const sttResponse = await fetch(LOCAL_STT_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio }),
    });

    const data = await sttResponse.json();

    if (sttResponse.ok) {
      console.log("✅ Transcription received:", data.transcript);
      return NextResponse.json({ transcript: data.transcript }, { status: 200 });
    } else {
      console.error("❌ Local STT API returned an error:", data);
      return NextResponse.json({ error: data.error || "Local STT API failed" }, { status: 500 });
    }
  } catch (error) {
    console.error("❌ Error processing audio:", error);
    return NextResponse.json({ error: "Failed to process audio" }, { status: 500 });
  }
}

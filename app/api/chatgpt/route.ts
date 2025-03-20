import { NextResponse } from "next/server";

const LLM_SERVER_URL = "https://fcd5-202-166-31-191.ngrok-free.app/chat"; // Update with your Ngrok URL

export async function POST(req: Request) {
  try {
    const { message } = await req.json();

    const response = await fetch(LLM_SERVER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    const data = await response.json();
    return NextResponse.json({ reply: data.response });

  } catch (error: any) {
    console.error("Error:", error.message);
    return NextResponse.json({ error: "Failed to fetch LLM response" }, { status: 500 });
  }
}

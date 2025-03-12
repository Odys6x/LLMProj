import { NextResponse } from "next/server";

const LAMBDA_URL = "https://zkcgerdd42chp6dw7v5fkypqlu0vfxew.lambda-url.us-east-1.on.aws/";

export async function POST(req: Request) {
  try {
    const { prompt } = await req.json();

    if (!prompt) {
      return NextResponse.json(
        { error: "Prompt is required" },
        { status: 400 }
      );
    }

    const response = await fetch(LAMBDA_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || "Failed to fetch response from AWS Lambda");
    }

    return NextResponse.json({ response: data.response });
  } catch (error: any) {
    console.error("Error fetching AWS Lambda response:", error.message);
    return NextResponse.json(
      { error: error.message || "Internal Server Error" },
      { status: 500 }
    );
  }
}

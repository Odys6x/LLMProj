import { NextResponse } from "next/server";
import { OpenAI } from "openai";

const openai = new OpenAI({
  apiKey: "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", // Ensure this is set in your `.env.local` file
});

export async function POST(req: Request) {
  try {
    const { message } = await req.json(); // Get the message sent by the user

    // Call the OpenAI API using the correct methods
    const response = await openai.chat.completions.create({
      model: "gpt-4o", // Ensure this matches the model you want to use
      messages: [
        { role: "system", content: "You are a helpful avatar assistant." },
        { role: "user", content: message },
      ],
    });

    const reply = response.choices[0]?.message?.content; // Retrieve the reply

    return NextResponse.json({ reply }); // Send the reply back to the frontend
  } catch (error: any) {
    console.error("Error calling OpenAI API:", error.message || error.response?.data);
    return NextResponse.json({ error: "Failed to fetch OpenAI response" }, { status: 500 });
  }
}

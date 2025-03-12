from flask import Flask, request, jsonify
import base64
import os
from openai import OpenAI

app = Flask(__name__)

# OpenAI API Key
OPENAI_API_KEY = "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"

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    try:
        data = request.json
        base64_audio = data.get("audio")

        if not base64_audio:
            return jsonify({"error": "No audio file provided"}), 400

        # Decode Base64 and save as WAV file
        audio_data = base64.b64decode(base64_audio.split(",")[1])
        audio_filename = "recorded_audio.wav"

        with open(audio_filename, "wb") as f:
            f.write(audio_data)

        # Transcribe using OpenAI Whisper
        client = OpenAI(api_key=OPENAI_API_KEY)

        with open(audio_filename, "rb") as audio_file:
            transcript = client.audio.translations.create(
                model="whisper-1",
                file=audio_file
            )

        return jsonify({"transcript": transcript.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

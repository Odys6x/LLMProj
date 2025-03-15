from flask import Blueprint, render_template, request, jsonify
import asyncio
from app.chat_router import handle_query

main = Blueprint("main", "name")

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    user_name = request.json.get("name")

    if user_message and user_name:
        response = asyncio.run(handle_query(user_message, user_name))
        return jsonify({"response": response})

    return jsonify({"response": "No message provided."})
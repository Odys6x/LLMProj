from flask import Blueprint, render_template, request, jsonify
import asyncio
from app.chat import custom_chain

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    user_name = request.json.get("name")
    if user_message and user_name:
        response = asyncio.run(custom_chain(user_message, user_name))
        return jsonify({"response": response})
    return jsonify({"response": "No message provided."})

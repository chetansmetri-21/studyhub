from flask import (
    Blueprint,
    request,
    jsonify
)

from app.utils.ai_engine import process_question
from app import limiter


ai_assistant = Blueprint(
    "ai_assistant",
    __name__,
    url_prefix="/ai"
)


@ai_assistant.route(
    "/ask",
    methods=["POST"]
)
@limiter.limit("20 per minute")
def ask():

    data = request.get_json(
        silent=True
    ) or {}

    message = data.get("message")

    if not isinstance(message, str):
        return jsonify({
            "type": "error",
            "message": "Please send your question as text."
        }), 400

    message = message.strip()

    if len(message) > 500:
        return jsonify({
            "type": "error",
            "message": "Please keep your question under 500 characters."
        }), 400

    result = process_question(
        message
    )

    return jsonify(
        result
    )
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

    message = data.get(
        "message",
        ""
    )

    result = process_question(
        message
    )

    return jsonify(
        result
    )
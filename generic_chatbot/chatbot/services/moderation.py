from django.conf import settings
from openai import OpenAI
from openai._compat import model_dump


def moderate_message(message: str, bot=None) -> str:
    """
    Send the user's message through OpenAI's moderation endpoint and
    return a non-empty string if the message should be blocked.

    Returns:
        A string with the category and score if blocked (e.g. "(harassment: 0.67)"),
        or an empty string if the content is acceptable.
    """
    # Call OpenAI moderation API
    moderation_response = OpenAI(api_key=settings.OPENAI_API_KEY).moderations.create(
        input=message,
        model="omni-moderation-latest",
    )

    # Extract category scores
    category_scores = moderation_response.results[0].category_scores or {}
    scores = model_dump(category_scores)

    # Determine if any score exceeds the configured threshold
    for category, score in scores.items():
        if score is None:
            continue
        if bot:
            threshold = bot.get_moderation_threshold(category)
        else:
            # Fallback to global defaults if no bot provided
            defaults = {
                "harassment": 0.5, "harassment/threatening": 0.1,
                "hate": 0.5, "hate/threatening": 0.1,
                "self-harm": 0.2, "self-harm/instructions": 0.5, "self-harm/intent": 0.7,
                "sexual": 0.5, "sexual/minors": 0.2,
                "violence": 0.7, "violence/graphic": 0.8
            }
            threshold = defaults.get(category, 1.0)

        if score > threshold:
            return category

    return ""

from django.conf import settings
from openai import OpenAI
from openai._compat import model_dump


def moderate_message(message: str) -> str:
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
        # Default threshold is 1.0 if not specified in settings
        threshold = settings.MODERATION_VALUES_FOR_BLOCKED.get(category, 1.0)
        if score > threshold:
            return category

    return ""

import json
import logging
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ..models import Keystroke

# Configure logging
logger = logging.getLogger(__name__)


@csrf_exempt  # Disable CSRF for testing; use authentication in production
def update_keystrokes(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            conversation_id = data.get("conversation_id")
            total_time_on_page = data.get("total_time_on_page")
            total_time_away_from_page = data.get("total_time_away_from_page")
            keystroke_count = data.get("keystroke_count")
            timestamp = data.get(
                "timestamp",
            )  # Optional: only needed if you're passing this in explicitly

            # Validate required fields
            if (
                conversation_id is None
                or total_time_on_page is None
                or total_time_away_from_page is None
                or keystroke_count is None
            ):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Parse timestamp if provided, else use current time
            if timestamp:
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    return JsonResponse(
                        {"error": "Invalid timestamp format. Use ISO 8601."},
                        status=400,
                    )
            else:
                timestamp = datetime.now()

            # Save keystroke
            keystroke = Keystroke.objects.create(
                conversation_id=conversation_id,
                total_time_on_page=total_time_on_page,
                total_time_away_from_page=total_time_away_from_page,
                keystroke_count=keystroke_count,
                timestamp=timestamp,
            )

            return JsonResponse(
                {
                    "message": "Keystroke data saved",
                    "keystroke_id": keystroke.id,
                },
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            logger.error(f"Error saving keystroke: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

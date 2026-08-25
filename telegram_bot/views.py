import json
import requests

from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from website.models import Booking
from website.telegram_notifications import send_booking_received


@csrf_exempt
def telegram_webhook(request):
    print("========== TELEGRAM WEBHOOK RECEIVED ==========")
    print("METHOD:", request.method)
    print("BODY:", request.body)

    # ---------------------------------------------------------
    # Only allow POST requests
    # ---------------------------------------------------------

    if request.method != "POST":
        return JsonResponse(
            {"status": "method not allowed"},
            status=405
        )

    try:
        # ---------------------------------------------------------
        # Parse Telegram update
        # ---------------------------------------------------------

        data = json.loads(request.body)

        message = data.get("message")

        if not message:
            print("No message found in Telegram update.")
            return JsonResponse({"ok": True})

        chat = message.get("chat")

        if not chat:
            print("No chat found in Telegram message.")
            return JsonResponse({"ok": True})

        chat_id = chat.get("id")
        text = message.get("text", "")

        print("CHAT ID:", chat_id)
        print("TEXT:", text)

        # ---------------------------------------------------------
        # Only process /start commands
        # ---------------------------------------------------------

        if not text.startswith("/start"):
            print("Not a /start command.")
            return JsonResponse({"ok": True})

        parts = text.split(maxsplit=1)

        # ---------------------------------------------------------
        # User opened the bot without a booking link
        # ---------------------------------------------------------

        if len(parts) < 2:
            print("No booking token provided.")

            send_telegram_message(
                chat_id,
                (
                    "Welcome to Ava's GLOW STUDIO. 👋\n\n"
                    "To enable Telegram reminders, please use "
                    "the Telegram reminder link from your booking "
                    "confirmation page."
                )
            )

            return JsonResponse({"ok": True})

        token = parts[1].strip()

        print("TOKEN RECEIVED:", token)
        print("TOKEN LENGTH:", len(token))

        # ---------------------------------------------------------
        # Validate Telegram booking token
        # ---------------------------------------------------------

        try:
            signer = signing.Signer()

            # The booking_success view replaces Django's ":"
            # separator with "_" for Telegram compatibility.
            #
            # Restore the original separator before unsigning.
            raw_token = token.replace("_", ":", 1)

            booking_id = signer.unsign(raw_token)

            print("BOOKING ID FROM TOKEN:", booking_id)

        except signing.BadSignature as e:

            print("INVALID TOKEN:", e)

            send_telegram_message(
                chat_id,
                (
                    "This reminder link is invalid or has expired. "
                    "Please make a new booking or contact "
                    "the barbershop."
                )
            )

            return JsonResponse({"ok": True})

        # ---------------------------------------------------------
        # Validate booking ID
        # ---------------------------------------------------------

        if not booking_id:
            print("No booking ID found in token.")

            send_telegram_message(
                chat_id,
                "We couldn't identify your booking."
            )

            return JsonResponse({"ok": True})

        # ---------------------------------------------------------
        # Find booking
        # ---------------------------------------------------------

        try:
            booking = Booking.objects.select_related(
                "service",
                "barber"
            ).get(id=booking_id)

            print("BOOKING FOUND:", booking.id)

        except Booking.DoesNotExist:

            print("BOOKING NOT FOUND:", booking_id)

            send_telegram_message(
                chat_id,
                "We couldn't find this booking."
            )

            return JsonResponse({"ok": True})

        # ---------------------------------------------------------
        # Connect Telegram to booking
        # ---------------------------------------------------------

        booking.telegram_chat_id = chat_id
        booking.telegram_reminder_enabled = True

        booking.save(
            update_fields=[
                "telegram_chat_id",
                "telegram_reminder_enabled",
            ]
        )

        print(
            "TELEGRAM CONNECTED TO BOOKING:",
            booking.id
        )

        # ---------------------------------------------------------
        # Send booking connection confirmation
        # ---------------------------------------------------------

        send_booking_received(booking)

        print(
            "BOOKING RECEIVED MESSAGE SENT:",
            booking.id
        )

        print(
            "========== TELEGRAM WEBHOOK SUCCESS =========="
        )

        return JsonResponse({"ok": True})

    except json.JSONDecodeError:

        print("INVALID JSON RECEIVED FROM TELEGRAM.")

        return JsonResponse(
            {"ok": False},
            status=400
        )

    except Exception as e:

        print(
            "========== TELEGRAM WEBHOOK ERROR =========="
        )

        print("ERROR:", repr(e))

        return JsonResponse(
            {"ok": False},
            status=500
        )


# ============================================================
# TELEGRAM SEND MESSAGE
# ============================================================

def send_telegram_message(chat_id, text):

    token = settings.TELEGRAM_BOT_TOKEN

    print(
        "========== SENDING TELEGRAM MESSAGE =========="
    )

    print(
        "TELEGRAM TOKEN EXISTS:",
        bool(token)
    )

    print(
        "CHAT ID:",
        chat_id
    )

    if not token:

        print(
            "ERROR: TELEGRAM_BOT_TOKEN IS MISSING"
        )

        return False

    url = (
        "https://api.telegram.org/"
        f"bot{token}/sendMessage"
    )

    try:

        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
            },
            timeout=10,
        )

        print(
            "TELEGRAM RESPONSE STATUS:",
            response.status_code
        )

        print(
            "TELEGRAM RESPONSE:",
            response.text
        )

        if response.ok:

            print(
                "TELEGRAM MESSAGE SENT SUCCESSFULLY"
            )

            return True

        print(
            "TELEGRAM MESSAGE FAILED"
        )

        return False

    except requests.RequestException as e:

        print(
            "TELEGRAM REQUEST ERROR:",
            repr(e)
        )

        return False



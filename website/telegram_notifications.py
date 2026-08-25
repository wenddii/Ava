import requests

from django.conf import settings


def send_telegram_message(chat_id, text):
    """
    Send a Telegram message to a specific chat.
    """

    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is missing")
        return False

    if not chat_id:
        print("ERROR: No Telegram chat ID provided")
        return False

    url = (
        f"https://api.telegram.org/"
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
            "Telegram notification:",
            response.status_code,
            response.text,
        )

        return response.ok

    except requests.RequestException as e:
        print("Telegram notification error:", repr(e))
        return False


def send_booking_received(booking):
    """
    Sent when the customer connects Telegram to a booking.
    """

    service_name = (
        booking.service.name
        if booking.service
        else "Selected service"
    )

    return send_telegram_message(
        booking.telegram_chat_id,
        (
            f"Hello {booking.customer_name}! 👋\n\n"
            "Your booking request has been received. ✅\n\n"
            f"📋 Booking ID: #{booking.id}\n"
            f"📅 Date: "
            f"{booking.appointment_date.strftime('%B %d, %Y')}\n"
            f"⏰ Time: "
            f"{booking.appointment_time.strftime('%I:%M %p')}\n"
            f"💈 Service: "
            f"{service_name}\n\n"
            "Your booking is currently pending confirmation "
            "from the barbershop.\n\n"
            "We will notify you here once your booking is confirmed."
        ),
    )


def send_booking_confirmed(booking):
    """
    Sent when the barbershop confirms the booking.
    """

    service_name = (
        booking.service.name
        if booking.service
        else "Selected service"
    )

    return send_telegram_message(
        booking.telegram_chat_id,
        (
            f"Hello {booking.customer_name}! 👋\n\n"
            "Your booking has been CONFIRMED! ✅🎉\n\n"
            f"📋 Booking ID: #{booking.id}\n"
            f"📅 Date: "
            f"{booking.appointment_date.strftime('%B %d, %Y')}\n"
            f"⏰ Time: "
            f"{booking.appointment_time.strftime('%I:%M %p')}\n"
            f"💈 Service: "
            f"{service_name}\n\n"
            "We look forward to seeing you at Ava's GLOW STUDIO."
        ),
    )


def send_booking_reminder(booking):
    """
    Send an appointment reminder.
    """

    service_name = (
        booking.service.name
        if booking.service
        else "Selected service"
    )

    return send_telegram_message(
        booking.telegram_chat_id,
        (
            f"Hello {booking.customer_name}! 👋\n\n"
            "⏰ APPOINTMENT REMINDER\n\n"
            f"📋 Booking ID: #{booking.id}\n"
            f"📅 Date: "
            f"{booking.appointment_date.strftime('%B %d, %Y')}\n"
            f"⏰ Time: "
            f"{booking.appointment_time.strftime('%I:%M %p')}\n"
            f"💈 Service: "
            f"{service_name}\n\n"
            "Your appointment at Ava's GLOW STUDIO is coming up.\n"
            "See you soon! 💈"
        ),
    )




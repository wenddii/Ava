from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.core import signing

from .forms import ContactForm, BookingForm
from .models import (
    ShopInfo,
    Service,
    GalleryImage,
    Barber,
    Testimonial,
    Booking,
)
from .utils import generate_available_slots, normalize_phone_number


def home(request):
    shop = ShopInfo.objects.first()
    services = Service.objects.all()
    gallery = GalleryImage.objects.all()
    barbers = Barber.objects.filter(is_available=True)
    testimonials = Testimonial.objects.all().order_by("-id")

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you! Your message has been sent successfully.")
            return redirect("home")
    else:
        form = ContactForm()

    context = {
        "shop": shop,
        "services": services,
        "gallery": gallery,
        "barbers": barbers,
        "testimonials": testimonials,
        "form": form,
    }
    return render(request, "website/home.html", context)


def available_slots_api(request):
    date_str = request.GET.get("date")
    service_id = request.GET.get("service")
    barber_id = request.GET.get("barber")

    if not date_str or not service_id:
        return JsonResponse({"slots": [], "error": "Date and Service are required."})

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"slots": [], "error": "Invalid date format."})

    try:
        service = Service.objects.get(id=service_id)
        duration = service.duration
    except Service.DoesNotExist:
        duration = 30

    b_id = int(barber_id) if barber_id and barber_id.isdigit() else None
    slots = generate_available_slots(selected_date, duration, b_id)

    formatted_slots = []
    for s in slots:
        val_str = s["value"] if isinstance(s, dict) else s
        t_obj = datetime.strptime(val_str, "%H:%M").time()
        formatted_slots.append({
            "value": val_str,
            "display": t_obj.strftime("%I:%M %p").lstrip("0")
        })

    return JsonResponse({
        "slots": formatted_slots,
        "date": date_str,
        "today": date.today().strftime("%Y-%m-%d"),
        "max_date": (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
    })


def booking_create(request):
    shop = ShopInfo.objects.first()
    services = Service.objects.all()
    barbers = Barber.objects.filter(is_available=True)
    today = date.today()
    max_date = today + timedelta(days=3)

    initial_service = request.GET.get("service")
    initial_barber = request.GET.get("barber")

    if request.method == "POST":
        form = BookingForm(request.POST, request.FILES)

        if form.is_valid():
            booking = form.save(commit=False)

            # Booking status
            booking.payment_status = "pending"
            booking.status = "pending"

            # Telegram reminder defaults
            booking.telegram_chat_id = None
            booking.telegram_reminder_enabled = False

            booking.save()

            messages.success(
                request,
                "Your booking request has been submitted! "
                "Please wait while our barber verifies your payment."
            )

            return redirect("booking_success", pk=booking.pk)

        else:
            messages.error(
                request,
                "Please correct the errors below to complete your booking."
            )

    else:
        initial_data = {
            "appointment_date": today.strftime("%Y-%m-%d"),
        }

        if initial_service and initial_service.isdigit():
            initial_data["service"] = initial_service

        if initial_barber and initial_barber.isdigit():
            initial_data["barber"] = initial_barber

        form = BookingForm(initial=initial_data)

    no_barbers_available = not barbers.exists()

    context = {
        "form": form,
        "shop": shop,
        "services": services,
        "barbers": barbers,
        "no_barbers_available": no_barbers_available,
        "today": today.strftime("%Y-%m-%d"),
        "max_date": max_date.strftime("%Y-%m-%d"),
    }

    return render(request, "website/booking.html", context)


def booking_success(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    shop = ShopInfo.objects.first()

    signer = signing.Signer()
    token = signer.sign(str(booking.id)).replace(":", "_")

    telegram_link = (
        f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}"
        f"?start={token}"
    )

    context = {
        "booking": booking,
        "shop": shop,
        "telegram_link": telegram_link,
    }

    return render(request, "website/booking_success.html", context)


def track_booking(request):
    shop = ShopInfo.objects.first()
    raw_phone = request.GET.get("phone", "").strip()
    searched = False
    bookings_list = []

    if raw_phone:
        searched = True
        norm_input = normalize_phone_number(raw_phone)

        # Exclude blocked administrative periods
        all_bookings = Booking.objects.exclude(booking_source="blocked").select_related("service", "barber")

        matched_bookings = []
        for b in all_bookings:
            b_norm = normalize_phone_number(b.phone_number)
            if norm_input and b_norm and (norm_input == b_norm or norm_input in b_norm or b_norm in norm_input):
                matched_bookings.append(b)
            elif raw_phone in b.phone_number:
                matched_bookings.append(b)

        today = date.today()
        upcoming = [b for b in matched_bookings if b.appointment_date >= today]
        past = [b for b in matched_bookings if b.appointment_date < today]

        upcoming.sort(key=lambda x: (x.appointment_date, x.appointment_time))
        past.sort(key=lambda x: (x.appointment_date, x.appointment_time), reverse=True)

        if upcoming:
            upcoming[0].is_next = True

        bookings_list = upcoming + past

    context = {
        "shop": shop,
        "phone_input": raw_phone,
        "searched": searched,
        "bookings": bookings_list,
    }
    return render(request, "website/track_booking.html", context)
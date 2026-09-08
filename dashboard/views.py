from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count, Max
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlsplit

from website.models import (
    ShopInfo,
    Service,
    GalleryImage,
    Barber,
    Booking,
)
from website.telegram_notifications import send_booking_confirmed
from .decorators import is_staff_user
from .forms import (
    ServiceForm,
    ShopInfoForm,
    GalleryImageForm,
    BarberForm,
    OfflineBookingForm,
)


def dashboard_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard_index")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return redirect("dashboard_index")
            else:
                messages.error(request, "Access denied. Only staff members can access the barber dashboard.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, "dashboard/login.html", {"form": form})


@login_required
@user_passes_test(is_staff_user)
def dashboard_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("dashboard_login")


@login_required
@user_passes_test(is_staff_user)
def dashboard_index(request):
    today = date.today()

    today_appointments = Booking.objects.filter(appointment_date=today).order_by("appointment_time")
    pending_payments = Booking.objects.filter(payment_status="pending").order_by("-created_at")
    upcoming_appointments = Booking.objects.filter(
        appointment_date__gt=today, status__in=["pending", "confirmed"]
    ).order_by("appointment_date", "appointment_time")[:10]

    context = {
        "today_count": today_appointments.count(),
        "pending_payments_count": pending_payments.count(),
        "confirmed_count": Booking.objects.filter(status="confirmed").count(),
        "completed_count": Booking.objects.filter(status="completed").count(),
        "today_appointments": today_appointments,
        "pending_payments": pending_payments[:5],
        "upcoming_appointments": upcoming_appointments,
        "latest_booking_id": Booking.objects.order_by("-id").values_list("id", flat=True).first() or 0,
    }
    return render(request, "dashboard/index.html", context)


@login_required
@user_passes_test(is_staff_user)
def dashboard_overview_data(request):
    today = date.today()
    booking_summary = Booking.objects.aggregate(
        today_count=Count("id", filter=Q(appointment_date=today)),
        pending_payments_count=Count("id", filter=Q(payment_status="pending")),
        confirmed_count=Count("id", filter=Q(status="confirmed")),
        completed_count=Count("id", filter=Q(status="completed")),
        latest_booking_id=Max("id"),
    )
    today_appointments = Booking.objects.filter(appointment_date=today).select_related("service").order_by("appointment_time")
    pending_payments = Booking.objects.filter(payment_status="pending").select_related("service").order_by("-created_at")[:5]

    def serialize_booking(booking):
        return {
            "id": booking.id,
            "detail_url": f"/dashboard/bookings/{booking.id}/",
            "customer_name": booking.customer_name,
            "phone_number": booking.phone_number or "",
            "service_name": booking.service.name if booking.service else "",
            "appointment_date": booking.appointment_date.strftime("%b %d, %Y"),
            "appointment_date_short": booking.appointment_date.strftime("%b %d"),
            "appointment_time": booking.appointment_time.strftime("%I:%M %p").lstrip("0"),
            "status": booking.status,
            "status_label": booking.get_status_display(),
            "has_payment_screenshot": bool(booking.payment_screenshot),
        }

    return JsonResponse({
        "stats": {
            "today_count": booking_summary["today_count"],
            "pending_payments_count": booking_summary["pending_payments_count"],
            "confirmed_count": booking_summary["confirmed_count"],
            "completed_count": booking_summary["completed_count"],
        },
        "latest_booking_id": booking_summary["latest_booking_id"],
        "today_appointments": [serialize_booking(booking) for booking in today_appointments],
        "pending_payments": [serialize_booking(booking) for booking in pending_payments],
    })


@login_required
@user_passes_test(is_staff_user)
def dashboard_bookings(request):
    status_filter = request.GET.get("status", "all")
    payment_filter = request.GET.get("payment", "all")
    source_filter = request.GET.get("source", "all")
    search_query = request.GET.get("q", "").strip()

    bookings = Booking.objects.all()

    if status_filter != "all":
        bookings = bookings.filter(status=status_filter)

    if payment_filter != "all":
        bookings = bookings.filter(payment_status=payment_filter)

    if source_filter != "all":
        bookings = bookings.filter(booking_source=source_filter)

    if search_query:
        bookings = bookings.filter(
            Q(customer_name__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )

    context = {
        "bookings": bookings,
        "status_filter": status_filter,
        "payment_filter": payment_filter,
        "source_filter": source_filter,
        "search_query": search_query,
    }
    return render(request, "dashboard/bookings.html", context)


@login_required
@user_passes_test(is_staff_user)
def dashboard_schedule(request):
    date_str = request.GET.get("date")
    barber_id = request.GET.get("barber")
    today = date.today()

    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    barbers = Barber.objects.all()
    b_id = int(barber_id) if barber_id and barber_id.isdigit() else None
    selected_barber = Barber.objects.filter(id=b_id).first() if b_id else None

    # Fetch active bookings for that date
    bookings_qs = Booking.objects.filter(
        appointment_date=selected_date,
        status__in=["pending", "confirmed"],
    )
    if selected_barber:
        bookings_qs = bookings_qs.filter(barber=selected_barber)

    # Build 30-minute interval slots from 09:00 to 20:00
    slots = []
    start_time = datetime.strptime("09:00", "%H:%M").time()
    end_time = datetime.strptime("20:00", "%H:%M").time()
    curr_dt = datetime.combine(selected_date, start_time)
    end_dt = datetime.combine(selected_date, end_time)

    while curr_dt < end_dt:
        t_val = curr_dt.time()
        matching_booking = None
        for b in bookings_qs:
            b_dur = b.service.duration if (b.service and b.service.duration) else 30
            b_start_dt = datetime.combine(selected_date, b.appointment_time)
            b_end_dt = b_start_dt + timedelta(minutes=b_dur)
            if b_start_dt <= curr_dt < b_end_dt:
                matching_booking = b
                break

        slots.append({
            "time_str": t_val.strftime("%H:%M"),
            "time_obj": t_val,
            "is_booked": matching_booking is not None,
            "booking": matching_booking,
        })
        curr_dt += timedelta(minutes=30)

    context = {
        "selected_date": selected_date.strftime("%Y-%m-%d"),
        "today": today.strftime("%Y-%m-%d"),
        "barbers": barbers,
        "selected_barber": selected_barber,
        "slots": slots,
    }
    return render(request, "dashboard/schedule.html", context)


@login_required
@user_passes_test(is_staff_user)
def dashboard_offline_booking_create(request):
    initial_source = request.GET.get("source", "phone")
    initial_date = request.GET.get("date", date.today().strftime("%Y-%m-%d"))
    initial_time = request.GET.get("time", "")
    initial_barber = request.GET.get("barber", "")

    if request.method == "POST":
        form = OfflineBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.payment_status = "verified"
            booking.status = "confirmed"
            if booking.booking_source == "blocked" and not booking.customer_name:
                booking.customer_name = "Blocked Time"
            booking.save()
            messages.success(
                request,
                f"Offline booking / blocked period recorded for {booking.appointment_date} at {booking.appointment_time}."
            )
            return redirect(f"/dashboard/schedule/?date={booking.appointment_date}")
        else:
            messages.error(request, "Error saving offline booking. Please check the form errors below.")
    else:
        initial_data = {
            "booking_source": initial_source,
            "appointment_date": initial_date,
            "appointment_time": initial_time,
        }
        if initial_barber and initial_barber.isdigit():
            initial_data["barber"] = initial_barber

        form = OfflineBookingForm(initial=initial_data)

    context = {
        "form": form,
        "services": Service.objects.all(),
        "barbers": Barber.objects.all(),
    }
    return render(request, "dashboard/offline_booking_form.html", context)


@login_required
@user_passes_test(is_staff_user)
def dashboard_booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    return_url_key = f"booking_return_url_{booking.pk}"

    if request.method == "GET":
        return_url = "/dashboard/bookings/"
        referer = request.META.get("HTTP_REFERER", "")
        if url_has_allowed_host_and_scheme(
            referer,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            referer_parts = urlsplit(referer)
            if referer_parts.path.startswith("/dashboard/"):
                return_url = referer_parts.path
                if referer_parts.query:
                    return_url += f"?{referer_parts.query}"
        request.session[return_url_key] = return_url

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "verify_payment":
            booking.payment_status = "verified"
            booking.status = "confirmed"
            booking.save()

            # Send Telegram confirmation
            if booking.telegram_reminder_enabled and booking.telegram_chat_id:
                send_booking_confirmed(booking)

            messages.success(
                request,
                f"Payment for Booking #{booking.id} verified and booking confirmed!"
            )

        elif action == "reject_payment":
            booking.payment_status = "rejected"
            booking.status = "cancelled"
            booking.save()

            messages.warning(
                request,
                f"Payment for Booking #{booking.id} rejected and booking cancelled."
            )

        elif action == "cancel_booking":
            booking.status = "cancelled"
            booking.save()

            messages.warning(
                request,
                f"Booking #{booking.id} cancelled."
            )

        elif action == "complete_booking":
            booking.status = "completed"
            booking.save()

            messages.success(
                request,
                f"Booking #{booking.id} marked as completed."
            )

        return redirect(request.session.pop(return_url_key, "/dashboard/bookings/"))

    return render(
        request,
        "dashboard/booking_detail.html",
        {"booking": booking}
    )


@login_required
@user_passes_test(is_staff_user)
def dashboard_services(request):
    services = Service.objects.all()
    edit_id = request.GET.get("edit")
    editing_service = None

    if edit_id and edit_id.isdigit():
        editing_service = get_object_or_404(Service, pk=int(edit_id))

    if request.method == "POST":
        if editing_service:
            form = ServiceForm(request.POST, instance=editing_service)
        else:
            form = ServiceForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Service saved successfully!")
            return redirect("dashboard_services")
    else:
        form = ServiceForm(instance=editing_service) if editing_service else ServiceForm()

    context = {
        "services": services,
        "form": form,
        "editing_service": editing_service,
    }
    return render(request, "dashboard/services.html", context)


@login_required
@user_passes_test(is_staff_user)
def dashboard_service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        try:
            service.delete()
            messages.success(request, "Service deleted successfully.")
        except Exception:
            messages.error(request, "Cannot delete service because historical bookings reference it.")
    return redirect("dashboard_services")


@login_required
@user_passes_test(is_staff_user)
def dashboard_gallery(request):
    images = GalleryImage.objects.all().order_by("-id")
    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Image uploaded to gallery.")
            return redirect("dashboard_gallery")
    else:
        form = GalleryImageForm()

    return render(request, "dashboard/gallery.html", {"images": images, "form": form})


@login_required
@user_passes_test(is_staff_user)
def dashboard_gallery_delete(request, pk):
    img = get_object_or_404(GalleryImage, pk=pk)
    if request.method == "POST":
        img.delete()
        messages.success(request, "Gallery image removed.")
    return redirect("dashboard_gallery")


@login_required
@user_passes_test(is_staff_user)
def dashboard_shop_info(request):
    shop = ShopInfo.objects.first()
    if request.method == "POST":
        if shop:
            form = ShopInfoForm(request.POST, request.FILES, instance=shop)
        else:
            form = ShopInfoForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, "Shop information and payment accounts updated.")
            return redirect("dashboard_shop_info")
    else:
        form = ShopInfoForm(instance=shop) if shop else ShopInfoForm()

    return render(request, "dashboard/shop_info.html", {"form": form, "shop": shop})


@login_required
@user_passes_test(is_staff_user)
def dashboard_barbers(request):
    barbers = Barber.objects.prefetch_related("services").all()
    edit_id = request.GET.get("edit")
    editing_barber = None

    if edit_id and edit_id.isdigit():
        editing_barber = get_object_or_404(Barber, pk=int(edit_id))

    if request.method == "POST":
        if editing_barber:
            form = BarberForm(request.POST, request.FILES, instance=editing_barber)
        else:
            form = BarberForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, "Barber saved successfully!")
            return redirect("dashboard_barbers")
    else:
        form = BarberForm(instance=editing_barber) if editing_barber else BarberForm()

    context = {
        "barbers": barbers,
        "form": form,
        "editing_barber": editing_barber,
    }
    return render(request, "dashboard/barbers.html", context)


@login_required
@user_passes_test(is_staff_user)
def dashboard_barbers_data(request):
    barbers = Barber.objects.prefetch_related("services").all()
    return JsonResponse({
        "barbers": [
            {
                "id": barber.id,
                "name": barber.name,
                "service_ids": list(barber.services.values_list("id", flat=True)),
                "services": [service.name for service in barber.services.all()],
            }
            for barber in barbers
        ]
    })


@login_required
@user_passes_test(is_staff_user)
def dashboard_barber_delete(request, pk):
    barber = get_object_or_404(Barber, pk=pk)
    if request.method == "POST":
        try:
            barber.delete()
            messages.success(request, "Barber deleted successfully.")
        except Exception:
            messages.error(request, "Cannot delete barber because existing bookings reference them.")
    return redirect("dashboard_barbers")


@login_required
@user_passes_test(is_staff_user)
def dashboard_barber_toggle_availability(request, pk):
    barber = get_object_or_404(Barber, pk=pk)
    if request.method == "POST":
        barber.is_available = not barber.is_available
        barber.save(update_fields=["is_available"])
        status = "available" if barber.is_available else "unavailable"
        messages.success(request, f"{barber.name} is now {status}.")
    return redirect("dashboard_barbers")

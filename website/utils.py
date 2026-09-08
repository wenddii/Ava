from datetime import date, datetime, time, timedelta
from django.db.models import Q
from django.utils import timezone


def generate_available_slots(selected_date, service_duration=30, barber_id=None):
    """
    Computes available 30-minute interval time slots for a given date,
    taking into account service duration, existing online & offline bookings,
    and blocked periods.

    Timezone: Africa/Addis_Ababa.
    """
    from website.models import Booking

    # Enforce 3-day advance limit
    today = date.today()
    max_date = today + timedelta(days=3)
    if selected_date < today or selected_date > max_date:
        return []

    # Operating hours: 09:00 AM to 08:00 PM (20:00)
    start_hour = 9
    end_hour = 20

    # Build potential slots in 30-min intervals
    potential_slots = []
    curr = datetime.combine(selected_date, time(start_hour, 0))
    end_dt = datetime.combine(selected_date, time(end_hour, 0))

    now_dt = datetime.now()

    while curr < end_dt:
        # Filter out past times for today
        if selected_date == today and curr <= now_dt:
            curr += timedelta(minutes=30)
            continue
        potential_slots.append(curr)
        curr += timedelta(minutes=30)

    # Fetch existing active bookings for that date
    bookings_qs = Booking.objects.filter(
        appointment_date=selected_date,
        status__in=["pending", "confirmed"],
    )

    if barber_id:
        bookings_qs = bookings_qs.filter(barber_id=barber_id)

    # Build booked time intervals
    booked_intervals = []
    for b in bookings_qs:
        b_duration = b.service.duration if (b.service and b.service.duration) else 30
        b_start = datetime.combine(selected_date, b.appointment_time)
        b_end = b_start + timedelta(minutes=b_duration)
        booked_intervals.append((b_start, b_end))

    available_slots = []
    for slot_dt in potential_slots:
        slot_end = slot_dt + timedelta(minutes=service_duration)

        # Check overlap with existing booked intervals
        is_overlapping = False
        for b_start, b_end in booked_intervals:
            if max(slot_dt, b_start) < min(slot_end, b_end):
                is_overlapping = True
                break

        if not is_overlapping:
            time_val = slot_dt.time().strftime("%H:%M")
            time_display = slot_dt.time().strftime("%I:%M %p").lstrip("0")
            available_slots.append({
                "value": time_val,
                "display": time_display,
            })

    return available_slots


def _active_booking_intervals(selected_date, barber_id=None):
    from website.models import AppointmentService, Booking

    active_statuses = ["pending", "confirmed"]
    segment_booking_ids = set(
        AppointmentService.objects.filter(
            booking__appointment_date=selected_date,
            booking__status__in=active_statuses,
        ).values_list("booking_id", flat=True)
    )
    segments = AppointmentService.objects.filter(
        booking__appointment_date=selected_date,
        booking__status__in=active_statuses,
    )
    if barber_id:
        segments = segments.filter(barber_id=barber_id)
    elif barber_id is None:
        segments = segments.filter(barber__isnull=True)

    intervals = [
        (
            datetime.combine(selected_date, segment.start_time),
            datetime.combine(selected_date, segment.end_time),
        )
        for segment in segments
    ]

    legacy_bookings = Booking.objects.filter(
        appointment_date=selected_date,
        status__in=active_statuses,
    ).exclude(id__in=segment_booking_ids)
    if barber_id:
        legacy_bookings = legacy_bookings.filter(Q(barber_id=barber_id) | Q(barber__isnull=True))
    else:
        legacy_bookings = legacy_bookings.filter(barber__isnull=True)

    for booking in legacy_bookings.select_related("service"):
        duration = booking.service.duration if booking.service else 30
        start = datetime.combine(selected_date, booking.appointment_time)
        intervals.append((start, start + timedelta(minutes=duration)))

    return intervals


def generate_sequential_available_slots(selected_date, assignments):
    """Return starts that fit every ordered service segment and assigned barber."""
    today = date.today()
    max_date = today + timedelta(days=3)
    if selected_date < today or selected_date > max_date or not assignments:
        return []

    now_dt = datetime.now()
    opening = datetime.combine(selected_date, time(9, 0))
    closing = datetime.combine(selected_date, time(20, 0))
    candidates = []
    current = opening
    while current < closing:
        if selected_date != today or current > now_dt:
            candidates.append(current)
        current += timedelta(minutes=30)

    intervals_by_barber = {}
    for assignment in assignments:
        barber_id = assignment.get("barber_id")
        if barber_id not in intervals_by_barber:
            intervals_by_barber[barber_id] = _active_booking_intervals(selected_date, barber_id)

    available = []
    for start in candidates:
        cursor = start
        valid = True
        for assignment in assignments:
            segment_end = cursor + timedelta(minutes=assignment["duration"])
            if segment_end > closing:
                valid = False
                break
            for booked_start, booked_end in intervals_by_barber[assignment.get("barber_id")]:
                if max(cursor, booked_start) < min(segment_end, booked_end):
                    valid = False
                    break
            if not valid:
                break
            cursor = segment_end
        if valid:
            available.append({
                "value": start.strftime("%H:%M"),
                "display": start.strftime("%I:%M %p").lstrip("0"),
            })
    return available


def normalize_phone_number(phone_str):
    """
    Normalizes Ethiopian phone number strings for matching.
    """
    if not phone_str:
        return ""
    digits = "".join([c for c in phone_str if c.isdigit()])
    if digits.startswith("251") and len(digits) == 12:
        digits = "0" + digits[3:]
    elif len(digits) == 9 and digits[0] in ["9", "7"]:
        digits = "0" + digits
    return digits

from django.db import models


class ShopInfo(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="shop/", blank=True, null=True)
    description = models.TextField()
    phone_number = models.CharField(max_length=20)
    location = models.CharField(max_length=200)
    opening_hours = models.CharField(max_length=200)
    payment_instructions = models.TextField(blank=True, help_text="Payment accounts info e.g. CBE / Telebirr numbers")
    instagram = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)


    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")

    def __str__(self):
        return f"{self.name} ({self.duration} mins)"


class GalleryImage(models.Model):
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.caption or f"Gallery Image {self.id}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.phone_number}"


class Testimonial(models.Model):
    customer_name = models.CharField(max_length=100)
    comment = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    image = models.ImageField(upload_to="testimonials/", blank=True, null=True)

    def __str__(self):
        return self.customer_name



class Barber(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    photo = models.ImageField(upload_to="paradise_barber/barbers/", blank=True, null=True)
    bio = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Booking(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    BOOKING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    BOOKING_SOURCE_CHOICES = [
        ("online", "Online"),
        ("phone", "Phone Call"),
        ("walk_in", "Walk-In"),
        ("blocked", "Blocked Time"),
    ]

    customer_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="bookings",
        null=True,
        blank=True
    )

    barber = models.ForeignKey(
        Barber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings"
    )

    appointment_date = models.DateField()
    appointment_time = models.TimeField()

    payment_screenshot = models.ImageField(
        upload_to="booking_payments/",
        null=True,
        blank=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending"
    )

    status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS_CHOICES,
        default="pending"
    )

    booking_source = models.CharField(
        max_length=20,
        choices=BOOKING_SOURCE_CHOICES,
        default="online"
    )

    notes = models.TextField(blank=True)

    # Telegram reminders
    telegram_chat_id = models.BigIntegerField(
        null=True,
        blank=True
    )

    telegram_reminder_enabled = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-appointment_date", "-appointment_time"]

    def __str__(self):
        source_lbl = self.get_booking_source_display()

        return (
            f"Booking #{self.id} [{source_lbl}] - "
            f"{self.customer_name} "
            f"({self.appointment_date} {self.appointment_time})"
        )
from django.contrib import admin
from .models import ShopInfo, Service, GalleryImage, ContactMessage, Testimonial, Barber, Booking


@admin.register(ShopInfo)
class ShopInfoAdmin(admin.ModelAdmin):
    list_display = ("name", "logo", "phone_number", "location", "opening_hours")



@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration")


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("id", "caption")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "created_at")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "rating", "image")



@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "is_available")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "phone_number", "service", "barber", "appointment_date", "appointment_time", "booking_source", "payment_status", "status")
    list_filter = ("booking_source", "payment_status", "status", "appointment_date", "barber")
    search_fields = ("customer_name", "phone_number")

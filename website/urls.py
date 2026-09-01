from django.urls import path
from . import views

urlpatterns = [
    # Public routes
    path("", views.home, name="home"),
    path("booking/", views.booking_create, name="booking"),
    path("booking/success/<int:pk>/", views.booking_success, name="booking_success"),
    path("track/", views.track_booking, name="track_booking"),
    path("api/available-slots/", views.available_slots_api, name="available_slots_api"),
]
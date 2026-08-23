from django.urls import path
from . import views

urlpatterns = [
    # Public routes
    path("", views.home, name="home"),
    path("booking/", views.booking_create, name="booking"),


    path("booking/success/<int:pk>/", views.booking_success, name="booking_success"),
    path("track/", views.track_booking, name="track_booking"),
    path("api/available-slots/", views.available_slots_api, name="available_slots_api"),

    # Dashboard / Staff routes
    path("dashboard/", views.dashboard_index, name="dashboard_index"),
    path("dashboard/schedule/", views.dashboard_schedule, name="dashboard_schedule"),
    path("dashboard/login/", views.dashboard_login, name="dashboard_login"),
    path("dashboard/logout/", views.dashboard_logout, name="dashboard_logout"),
    path("dashboard/bookings/", views.dashboard_bookings, name="dashboard_bookings"),
    path("dashboard/bookings/add-offline/", views.dashboard_offline_booking_create, name="dashboard_offline_booking_create"),
    path("dashboard/bookings/<int:pk>/", views.dashboard_booking_detail, name="dashboard_booking_detail"),

    path("dashboard/services/", views.dashboard_services, name="dashboard_services"),
    path("dashboard/services/delete/<int:pk>/", views.dashboard_service_delete, name="dashboard_service_delete"),
    path("dashboard/gallery/", views.dashboard_gallery, name="dashboard_gallery"),
    path("dashboard/gallery/delete/<int:pk>/", views.dashboard_gallery_delete, name="dashboard_gallery_delete"),
    path("dashboard/shop/", views.dashboard_shop_info, name="dashboard_shop_info"),
    path("dashboard/barbers/", views.dashboard_barbers, name="dashboard_barbers"),
    path("dashboard/barbers/delete/<int:pk>/", views.dashboard_barber_delete, name="dashboard_barber_delete"),
    path("dashboard/barbers/<int:pk>/toggle-availability/", views.dashboard_barber_toggle_availability, name="dashboard_barber_toggle_availability"),
    
]
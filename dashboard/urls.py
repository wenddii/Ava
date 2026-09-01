from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_index, name="dashboard_index"),
    path("schedule/", views.dashboard_schedule, name="dashboard_schedule"),
    path("login/", views.dashboard_login, name="dashboard_login"),
    path("logout/", views.dashboard_logout, name="dashboard_logout"),
    path("bookings/", views.dashboard_bookings, name="dashboard_bookings"),
    path("bookings/add-offline/", views.dashboard_offline_booking_create, name="dashboard_offline_booking_create"),
    path("bookings/<int:pk>/", views.dashboard_booking_detail, name="dashboard_booking_detail"),
    path("services/", views.dashboard_services, name="dashboard_services"),
    path("services/delete/<int:pk>/", views.dashboard_service_delete, name="dashboard_service_delete"),
    path("gallery/", views.dashboard_gallery, name="dashboard_gallery"),
    path("gallery/delete/<int:pk>/", views.dashboard_gallery_delete, name="dashboard_gallery_delete"),
    path("shop/", views.dashboard_shop_info, name="dashboard_shop_info"),
    path("barbers/", views.dashboard_barbers, name="dashboard_barbers"),
    path("barbers/delete/<int:pk>/", views.dashboard_barber_delete, name="dashboard_barber_delete"),
    path("barbers/<int:pk>/toggle-availability/", views.dashboard_barber_toggle_availability, name="dashboard_barber_toggle_availability"),
]

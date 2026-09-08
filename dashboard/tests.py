from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from website.models import ShopInfo, Service, Barber, Booking


class DashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.shop = ShopInfo.objects.create(
            name="Ava's GLOW STUDIO",
            description="Luxury grooming",
            phone_number="0911223344",
            location="Addis Ababa",
            opening_hours="09:00 AM - 08:00 PM",
            payment_instructions="CBE: 1000123456"
        )
        self.service = Service.objects.create(
            name="Haircut",
            description="Standard haircut",
            price=300.00,
            duration=30
        )
        self.barber = Barber.objects.create(
            name="Abebe",
            role="Senior Barber"
        )

        self.dummy_image = SimpleUploadedFile(
            name="test_receipt.gif",
            content=b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif"
        )

        self.staff_user = User.objects.create_user(
            username="barber_admin",
            email="admin@barber.com",
            password="password123",
            is_staff=True
        )

    def test_dashboard_access_control(self):
        # Unauthenticated user should be redirected to login
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

        # Log in as staff
        self.client.login(username="barber_admin", password="password123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_payment_verification_and_booking_confirmation(self):
        today = date.today()
        booking = Booking.objects.create(
            customer_name="Jane Smith",
            phone_number="0922334455",
            service=self.service,
            barber=self.barber,
            appointment_date=today + timedelta(days=1),
            appointment_time="14:00:00",
            payment_screenshot=self.dummy_image,
            payment_status="pending",
            status="pending"
        )

        self.client.login(username="barber_admin", password="password123")
        
        # Verify payment
        response = self.client.post(f"/dashboard/bookings/{booking.id}/", {"action": "verify_payment"})
        self.assertEqual(response.status_code, 302)

        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, "verified")
        self.assertEqual(booking.status, "confirmed")

        # Mark completed
        response = self.client.post(f"/dashboard/bookings/{booking.id}/", {"action": "complete_booking"})
        booking.refresh_from_db()
        self.assertEqual(booking.status, "completed")

    def test_booking_update_returns_to_dashboard_referrer(self):
        booking = Booking.objects.create(
            customer_name="Jane Smith",
            phone_number="0922334455",
            service=self.service,
            barber=self.barber,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time="14:00:00",
            payment_screenshot=self.dummy_image,
            payment_status="pending",
            status="pending"
        )
        self.client.login(username="barber_admin", password="password123")

        self.client.get(
            f"/dashboard/bookings/{booking.id}/",
            HTTP_REFERER="http://testserver/dashboard/",
        )
        response = self.client.post(
            f"/dashboard/bookings/{booking.id}/",
            {"action": "complete_booking"},
        )
        self.assertEqual(response.url, "/dashboard/")

        self.client.get(
            f"/dashboard/bookings/{booking.id}/",
            HTTP_REFERER="http://testserver/dashboard/bookings/?status=pending",
        )
        response = self.client.post(
            f"/dashboard/bookings/{booking.id}/",
            {"action": "cancel_booking"},
        )
        self.assertEqual(response.url, "/dashboard/bookings/?status=pending")

        response = self.client.post(
            f"/dashboard/bookings/{booking.id}/",
            {"action": "complete_booking"},
        )
        self.assertEqual(response.url, "/dashboard/bookings/")

    def test_offline_and_blocked_time_appointments(self):
        self.client.login(username="barber_admin", password="password123")
        target_date = date.today() + timedelta(days=1)

        # 1. Create a Walk-In appointment
        response = self.client.post("/dashboard/bookings/add-offline/", {
            "booking_source": "walk_in",
            "customer_name": "Solomon Walkin",
            "phone_number": "0912345678",
            "service": self.service.id,
            "barber": self.barber.id,
            "appointment_date": target_date.strftime("%Y-%m-%d"),
            "appointment_time": "11:00",
        })
        self.assertEqual(response.status_code, 302)

        # 2. Block time slot at 15:00
        response = self.client.post("/dashboard/bookings/add-offline/", {
            "booking_source": "blocked",
            "customer_name": "Lunch Break",
            "barber": self.barber.id,
            "appointment_date": target_date.strftime("%Y-%m-%d"),
            "appointment_time": "15:00",
        })
        self.assertEqual(response.status_code, 302)

        # 3. Verify schedule view renders blocked and walk-in statuses
        sched_response = self.client.get(f"/dashboard/schedule/?date={target_date.strftime('%Y-%m-%d')}")
        self.assertEqual(sched_response.status_code, 200)
        self.assertContains(sched_response, "Solomon Walkin")
        self.assertContains(sched_response, "Lunch Break")

    def test_shop_info_update(self):
        self.client.login(username="barber_admin", password="password123")
        logo_upload = SimpleUploadedFile(
            name="new_logo.gif",
            content=b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif"
        )
        response = self.client.post("/dashboard/shop/", {
            "name": "Ava's GLOW STUDIO",
            "phone_number": "0911998877",
            "location": "Bole, Addis Ababa",
            "opening_hours": "08:00 AM - 09:00 PM",
            "description": "Luxury barbershop",
            "payment_instructions": "CBE: 1000123456",
            "logo": logo_upload,
        })
        self.assertEqual(response.status_code, 302)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, "Ava's GLOW STUDIO")
        self.assertTrue(bool(self.shop.logo))

    def test_staff_services_can_be_added_edited_shared_and_removed(self):
        beard_trim = Service.objects.create(
            name="Beard Trim",
            description="Beard trim",
            price=150.00,
            duration=20,
        )
        second_barber = Barber.objects.create(name="Sara", role="Stylist")
        self.client.login(username="barber_admin", password="password123")

        response = self.client.post("/dashboard/barbers/", {
            "name": "Abraham",
            "role": "Senior Barber",
            "services": [self.service.id, beard_trim.id],
        })
        self.assertEqual(response.status_code, 302)
        assigned_barber = Barber.objects.get(name="Abraham")
        self.assertEqual(set(assigned_barber.services.values_list("id", flat=True)), {self.service.id, beard_trim.id})

        response = self.client.get(f"/dashboard/barbers/?edit={assigned_barber.id}")
        self.assertContains(response, f'name="services" value="{self.service.id}" checked')
        self.assertContains(response, f'name="services" value="{beard_trim.id}" checked')

        response = self.client.post(f"/dashboard/barbers/?edit={assigned_barber.id}", {
            "name": assigned_barber.name,
            "role": assigned_barber.role,
            "services": [beard_trim.id],
        })
        self.assertEqual(response.status_code, 302)
        assigned_barber.refresh_from_db()
        self.assertEqual(list(assigned_barber.services.values_list("id", flat=True)), [beard_trim.id])

        second_barber.services.add(beard_trim)
        data = self.client.get("/dashboard/barbers/data/").json()
        barber_data = {item["id"]: item for item in data["barbers"]}
        self.assertEqual(barber_data[assigned_barber.id]["service_ids"], [beard_trim.id])
        self.assertEqual(barber_data[second_barber.id]["service_ids"], [beard_trim.id])

    def test_dashboard_url_reversal(self):
        from django.urls import reverse
        self.assertEqual(reverse("dashboard_index"), "/dashboard/")
        self.assertEqual(reverse("dashboard_schedule"), "/dashboard/schedule/")
        self.assertEqual(reverse("dashboard_login"), "/dashboard/login/")
        self.assertEqual(reverse("dashboard_logout"), "/dashboard/logout/")
        self.assertEqual(reverse("dashboard_bookings"), "/dashboard/bookings/")
        self.assertEqual(reverse("dashboard_offline_booking_create"), "/dashboard/bookings/add-offline/")
        self.assertEqual(reverse("dashboard_booking_detail", args=[1]), "/dashboard/bookings/1/")
        self.assertEqual(reverse("dashboard_services"), "/dashboard/services/")
        self.assertEqual(reverse("dashboard_service_delete", args=[1]), "/dashboard/services/delete/1/")
        self.assertEqual(reverse("dashboard_gallery"), "/dashboard/gallery/")
        self.assertEqual(reverse("dashboard_gallery_delete", args=[1]), "/dashboard/gallery/delete/1/")
        self.assertEqual(reverse("dashboard_shop_info"), "/dashboard/shop/")
        self.assertEqual(reverse("dashboard_barbers"), "/dashboard/barbers/")
        self.assertEqual(reverse("dashboard_barbers_data"), "/dashboard/barbers/data/")
        self.assertEqual(reverse("dashboard_barber_delete", args=[1]), "/dashboard/barbers/delete/1/")
        self.assertEqual(reverse("dashboard_barber_toggle_availability", args=[1]), "/dashboard/barbers/1/toggle-availability/")

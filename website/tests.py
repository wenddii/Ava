from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from website.models import ShopInfo, Service, Barber, Booking


class BookingSystemTests(TestCase):
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

        # Create dummy image for payment screenshot
        self.dummy_image = SimpleUploadedFile(
            name="test_receipt.gif",
            content=b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif"
        )

        # Create staff user for dashboard
        self.staff_user = User.objects.create_user(
            username="barber_admin",
            email="admin@barber.com",
            password="password123",
            is_staff=True
        )

    def test_booking_creation_and_3day_limit(self):
        today = date.today()
        valid_date = today + timedelta(days=2)
        invalid_date = today + timedelta(days=5)

        # Valid booking
        booking = Booking.objects.create(
            customer_name="John Doe",
            phone_number="0911000111",
            service=self.service,
            barber=self.barber,
            appointment_date=valid_date,
            appointment_time="10:00:00",
            payment_screenshot=self.dummy_image,
            payment_status="pending",
            status="pending"
        )
        self.assertEqual(booking.payment_status, "pending")
        self.assertEqual(booking.status, "pending")

        # Test booking API endpoint slot logic
        response = self.client.get(f"/api/available-slots/?date={valid_date.strftime('%Y-%m-%d')}&service={self.service.id}&barber={self.barber.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        slot_values = [s["value"] for s in data["slots"]]
        self.assertNotIn("10:00", slot_values)  # 10:00 is booked, should not be available

        # Test invalid date API endpoint
        response = self.client.get(f"/api/available-slots/?date={invalid_date.strftime('%Y-%m-%d')}&service={self.service.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slots"], [])

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

    def test_english_date_and_time_rendering(self):
        # Verify slot API returns 12-hour AM/PM English formatted times
        today = date.today() + timedelta(days=1)
        response = self.client.get(f"/api/available-slots/?date={today.strftime('%Y-%m-%d')}&service={self.service.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data["slots"]) > 0)
        first_slot = data["slots"][0]
        self.assertIn("AM", first_slot["display"])

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

        # 3. Verify public API slot logic excludes 11:00 and 15:00 for online customers
        api_response = self.client.get(f"/api/available-slots/?date={target_date.strftime('%Y-%m-%d')}&service={self.service.id}&barber={self.barber.id}")
        data = api_response.json()
        slot_values = [s["value"] for s in data["slots"]]
        self.assertNotIn("11:00", slot_values)
        self.assertNotIn("15:00", slot_values)

        # 4. Verify schedule view renders blocked and walk-in statuses
        sched_response = self.client.get(f"/dashboard/schedule/?date={target_date.strftime('%Y-%m-%d')}")
        self.assertEqual(sched_response.status_code, 200)
        self.assertContains(sched_response, "Solomon Walkin")
        self.assertContains(sched_response, "Lunch Break")

    def test_testimonial_with_and_without_image(self):
        from website.models import Testimonial

        # Testimonial 1: Without image
        t1 = Testimonial.objects.create(
            customer_name="Dawit Tech",
            comment="Great service!",
            rating=5
        )

        # Testimonial 2: With image
        t2 = Testimonial.objects.create(
            customer_name="Sara Barber",
            comment="Best haircut in town",
            rating=5,
            image=self.dummy_image
        )

        # Check public home page rendering
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dawit Tech")
        self.assertContains(response, "Sara Barber")
        self.assertContains(response, "D")

    def test_shop_logo_rendering_and_fallback(self):
        # 1. Test fallback name when no logo exists
        self.shop.logo = None
        self.shop.save()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.shop.name)

        # 2. Upload logo image
        logo_file = SimpleUploadedFile(name="logo.gif", content=b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif")
        self.shop.logo = logo_file
        self.shop.save()

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.shop.logo.url)

        # 3. Test Staff Dashboard Shop Info update with logo upload
        self.client.login(username="barber_admin", password="password123")
        logo_upload = SimpleUploadedFile(name="new_logo.gif", content=b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif")
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

    def test_customer_booking_tracking(self):
        today = date.today()
        # 1. Create a booking with phone number
        b1 = Booking.objects.create(
            customer_name="Customer One",
            phone_number="0911554433",
            service=self.service,
            barber=self.barber,
            appointment_date=today + timedelta(days=1),
            appointment_time="10:00:00",
            payment_status="pending",
            status="pending",
            notes="Private customer note"
        )
        # 2. Create another booking with same phone number
        b2 = Booking.objects.create(
            customer_name="Customer One",
            phone_number="0911554433",
            service=self.service,
            barber=self.barber,
            appointment_date=today + timedelta(days=2),
            appointment_time="14:00:00",
            payment_status="verified",
            status="confirmed"
        )
        # 3. Create a booking for another customer
        b_other = Booking.objects.create(
            customer_name="Other Customer",
            phone_number="0988776655",
            service=self.service,
            appointment_date=today + timedelta(days=1),
            appointment_time="15:00:00"
        )

        # Access track booking page without submitting
        response = self.client.get("/track/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Track My Booking")

        # Track with phone number (test formatted and exact)
        response = self.client.get("/track/?phone=0911554433")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Haircut")
        self.assertContains(response, "Abebe")
        self.assertContains(response, "Pending")
        self.assertContains(response, "Confirmed")

        # Privacy checks: DB IDs, private notes, other customer names should not be exposed
        self.assertNotContains(response, f"#{b1.id}")
        self.assertNotContains(response, f"#{b2.id}")
        self.assertNotContains(response, "Private customer note")
        self.assertNotContains(response, "Other Customer")

        # Test phone number variant (e.g., +251 911 554 433)
        response_variant = self.client.get("/track/?phone=%2B251911554433")
        self.assertEqual(response_variant.status_code, 200)
        self.assertContains(response_variant, "Haircut")

        # Test non-existent phone number
        response_empty = self.client.get("/track/?phone=0900000000")
        self.assertEqual(response_empty.status_code, 200)
        self.assertContains(response_empty, "We couldn't find any bookings for this phone number.")
        self.assertNotContains(response_empty, "Customer One")
        self.assertNotContains(response_empty, "Other Customer")


from datetime import date, timedelta
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from website.models import ShopInfo, Service, Barber, Booking, AppointmentService
import json


class WebsitePublicTests(TestCase):
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

    def test_english_date_and_time_rendering(self):
        # Verify slot API returns 12-hour AM/PM English formatted times
        today = date.today() + timedelta(days=1)
        response = self.client.get(f"/api/available-slots/?date={today.strftime('%Y-%m-%d')}&service={self.service.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data["slots"]) > 0)
        first_slot = data["slots"][0]
        self.assertIn("AM", first_slot["display"])

    def test_multi_service_booking_uses_eligible_stylists_and_sequential_slots(self):
        manicure = Service.objects.create(
            name="Manicure",
            description="Nail care",
            price=400.00,
            duration=45,
        )
        second_barber = Barber.objects.create(name="Sara", role="Stylist")
        self.barber.services.add(self.service)
        second_barber.services.add(manicure)
        target_date = date.today() + timedelta(days=1)

        eligible = self.client.get(f"/api/eligible-barbers/?service={self.service.id}")
        self.assertEqual(eligible.status_code, 200)
        self.assertEqual([item["id"] for item in eligible.json()["barbers"]], [self.barber.id])

        existing = Booking.objects.create(
            customer_name="Existing Customer",
            phone_number="0911999000",
            service=manicure,
            barber=second_barber,
            appointment_date=target_date,
            appointment_time="10:30:00",
            payment_status="pending",
            status="pending",
        )
        AppointmentService.objects.create(
            booking=existing,
            service=manicure,
            barber=second_barber,
            sequence=1,
            duration=manicure.duration,
            price=manicure.price,
            start_time="10:30:00",
            end_time="11:15:00",
        )

        assignments = [
            {"service_id": self.service.id, "barber_id": self.barber.id},
            {"service_id": manicure.id, "barber_id": second_barber.id},
        ]
        slots = self.client.get(
            f"/api/available-slots/?date={target_date:%Y-%m-%d}&assignments={json.dumps(assignments)}"
        )
        self.assertEqual(slots.status_code, 200)
        self.assertNotIn("10:00", [slot["value"] for slot in slots.json()["slots"]])

        response = self.client.post("/booking/", {
            "customer_name": "Multi Service Customer",
            "phone_number": "0911223344",
            "service": self.service.id,
            "barber": self.barber.id,
            "appointment_date": target_date.strftime("%Y-%m-%d"),
            "appointment_time": "12:00",
            "appointment_services": json.dumps(assignments),
            "notes": "Sequential appointment",
            "payment_screenshot": self.dummy_image,
        })
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get(customer_name="Multi Service Customer")
        segments = list(booking.appointment_services.all())
        self.assertEqual(len(segments), 2)
        self.assertEqual([segment.sequence for segment in segments], [1, 2])
        self.assertEqual([segment.barber_id for segment in segments], [self.barber.id, second_barber.id])
        self.assertEqual(segments[0].start_time.strftime("%H:%M"), "12:00")
        self.assertEqual(segments[0].end_time.strftime("%H:%M"), "12:30")
        self.assertEqual(segments[1].start_time.strftime("%H:%M"), "12:30")
        self.assertEqual(segments[1].end_time.strftime("%H:%M"), "13:15")

    def test_eligible_stylists_are_limited_to_service_assignments(self):
        manicure = Service.objects.create(
            name="Manicure",
            description="Nail care",
            price=400.00,
            duration=45,
        )
        sara = Barber.objects.create(name="Sara", role="Stylist")
        self.barber.services.add(self.service)
        sara.services.add(manicure)

        haircut_response = self.client.get(f"/api/eligible-barbers/?service={self.service.id}")
        manicure_response = self.client.get(f"/api/eligible-barbers/?service={manicure.id}")

        self.assertEqual([barber["id"] for barber in haircut_response.json()["barbers"]], [self.barber.id])
        self.assertEqual([barber["id"] for barber in manicure_response.json()["barbers"]], [sara.id])

    def test_unassigned_service_has_no_stylists_and_invalid_assignment_is_rejected(self):
        unassigned = Service.objects.create(
            name="Hair Coloring",
            description="Color treatment",
            price=600.00,
            duration=60,
        )
        eligible = self.client.get(f"/api/eligible-barbers/?service={unassigned.id}")
        self.assertEqual(eligible.status_code, 200)
        self.assertEqual(eligible.json()["barbers"], [])

        invalid = self.client.get(
            f"/api/available-slots/?date={(date.today() + timedelta(days=1)):%Y-%m-%d}"
            f"&assignments={json.dumps([{'service_id': unassigned.id, 'barber_id': self.barber.id}])}"
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["error"], "This stylist is unavailable for this service.")

    def test_booking_page_has_service_first_stylist_flow(self):
        response = self.client.get("/booking/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Service")
        self.assertContains(response, "Stylist")
        self.assertContains(response, "Summary")
        self.assertContains(response, "Services")
        self.assertContains(response, "Confirm")
        self.assertNotContains(response, "Preferred Stylist")

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

from django import forms
from datetime import date, datetime, timedelta
from django.core.exceptions import ValidationError
from .models import ContactMessage, Booking, Service, ShopInfo, GalleryImage, Barber


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "phone_number", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Your Full Name"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "How can we help you?"}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            "customer_name",
            "phone_number",
            "service",
            "barber",
            "appointment_date",
            "appointment_time",
            "payment_screenshot",
            "notes",
        ]
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name", "required": "required"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 0911223344", "required": "required"}),
            "service": forms.Select(attrs={"class": "form-select", "required": "required", "id": "id_service"}),
            "barber": forms.Select(attrs={"class": "form-select", "id": "id_barber"}),
            "appointment_date": forms.DateInput(attrs={"class": "form-control", "type": "date", "required": "required", "id": "id_appointment_date"}),
            "appointment_time": forms.TimeInput(attrs={"class": "form-control", "type": "time", "required": "required", "id": "id_appointment_time"}),
            "payment_screenshot": forms.FileInput(attrs={"class": "form-control", "accept": "image/*", "required": "required"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Any special instructions or preferences (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["barber"].queryset = Barber.objects.filter(is_available=True)

    def clean_appointment_date(self):
        appt_date = self.cleaned_data.get("appointment_date")
        today = date.today()
        max_date = today + timedelta(days=3)

        if appt_date < today:
            raise ValidationError("You cannot book an appointment for a past date.")
        if appt_date > max_date:
            raise ValidationError(f"Bookings are only allowed up to 3 days in advance (until {max_date.strftime('%b %d, %Y')}).")

        return appt_date

    def clean(self):
        cleaned_data = super().clean()
        appt_date = cleaned_data.get("appointment_date")
        appt_time = cleaned_data.get("appointment_time")
        barber = cleaned_data.get("barber")

        if appt_date and appt_time:
            today = date.today()
            now_time = datetime.now().time()
            if appt_date == today and appt_time < now_time:
                self.add_error("appointment_time", "You cannot book a time slot in the past.")

            # Duplicate active booking check
            query = Booking.objects.filter(
                appointment_date=appt_date,
                appointment_time=appt_time,
                status__in=["pending", "confirmed"],
            )
            if barber:
                query = query.filter(barber=barber)

            if query.exists():
                self.add_error(
                    "appointment_time",
                    "This time slot is already booked. Please select a different date or time."
                )

        return cleaned_data


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "price", "duration"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "duration": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Duration in minutes"}),
        }


class ShopInfoForm(forms.ModelForm):
    class Meta:
        model = ShopInfo
        fields = ["name", "logo", "description", "phone_number", "location", "opening_hours", "payment_instructions", "instagram", "tiktok"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "opening_hours": forms.TextInput(attrs={"class": "form-control"}),
            "payment_instructions": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "e.g. CBE Account: 10001234567 (Africa Barber Shop), Telebirr: 0911223344"}),
            "instagram": forms.URLInput(attrs={"class": "form-control"}),
            "tiktok": forms.URLInput(attrs={"class": "form-control"}),
        }



class GalleryImageForm(forms.ModelForm):
    class Meta:
        model = GalleryImage
        fields = ["image", "caption"]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "caption": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional caption"}),
        }


class BarberForm(forms.ModelForm):
    class Meta:
        model = Barber
        fields = ["name", "role", "photo", "bio"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.TextInput(attrs={"class": "form-control"}),
            "photo": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class OfflineBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            "booking_source",
            "customer_name",
            "phone_number",
            "service",
            "barber",
            "appointment_date",
            "appointment_time",
            "notes",
        ]
        widgets = {
            "booking_source": forms.Select(attrs={"class": "form-select", "id": "id_booking_source"}),
            "customer_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Customer Name / Block Label"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number (optional)"}),
            "service": forms.Select(attrs={"class": "form-select"}),
            "barber": forms.Select(attrs={"class": "form-select"}),
            "appointment_date": forms.DateInput(attrs={"class": "form-control", "type": "date", "required": "required"}),
            "appointment_time": forms.TimeInput(attrs={"class": "form-control", "type": "time", "required": "required"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Notes / Reason"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get("booking_source")
        c_name = cleaned_data.get("customer_name")
        appt_date = cleaned_data.get("appointment_date")
        appt_time = cleaned_data.get("appointment_time")
        barber = cleaned_data.get("barber")

        if source == "blocked" and not c_name:
            cleaned_data["customer_name"] = "Blocked Time"

        if source in ["phone", "walk_in"] and not c_name:
            self.add_error("customer_name", "Customer name is required for phone or walk-in appointments.")

        if appt_date and appt_time:
            query = Booking.objects.filter(
                appointment_date=appt_date,
                appointment_time=appt_time,
                status__in=["pending", "confirmed"],
            )
            if barber:
                query = query.filter(barber=barber)

            if query.exists():
                self.add_error(
                    "appointment_time",
                    "A booking or blocked period already exists for this barber, date, and time slot."
                )

        return cleaned_data
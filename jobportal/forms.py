import re
import phonenumbers

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import CandidateProfile
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError


class RegistrationForm(UserCreationForm):
    username = forms.CharField(
        label="Username",
        max_length=150,
        help_text="",
        error_messages={
            "required": "Please enter a username.",
            "max_length": "Your username must be 150 characters or fewer.",
        },
        widget=forms.TextInput(attrs={
            "placeholder": "Choose a username",
            "autocomplete": "username",
        }),
    )

    email = forms.EmailField(
        label="Email address",
        required=True,
        error_messages={
            "required": "Please enter your email address.",
            "invalid": "Enter a valid email address.",
        },
        widget=forms.EmailInput(attrs={
            "placeholder": "you@example.com",
            "autocomplete": "email",
        }),
    )

    password1 = forms.CharField(
        label="Password",
        strip=False,
        help_text="",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Create a strong password",
            "autocomplete": "new-password",
        }),
    )

    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        help_text="",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Enter your password again",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.help_text = ""

        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-input"

    def clean_email(self):
        email = self.cleaned_data["email"].strip()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. "
                "Please log in or use another email."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

        return user


class CandidateProfileForm(forms.ModelForm):
    phone = forms.CharField(
        label="Phone number",
        required=True,
        max_length=25,
        widget=forms.TextInput(attrs={
            "id": "id_phone",
            "placeholder": "Enter phone number",
            "type": "tel",
            "autocomplete": "tel",
        }),
        error_messages={
            "required": "Phone number is required.",
        },
    )

    class Meta:
        model = CandidateProfile
        fields = [
            "full_name",
            "phone",
            "location",
            "education",
            "graduation_year",
            "experience_level",
            "skills",
            "preferred_job_roles",
            "preferred_locations",
            "expected_salary",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Enter your full name",
                "autocomplete": "name",
            }),
            "location": forms.TextInput(attrs={
                "placeholder": "City, state, country",
            }),
            "skills": forms.Textarea(attrs={
                "placeholder": "Example: SQL, HTML, CSS, JavaScript",
                "rows": 3,
            }),
            "preferred_job_roles": forms.TextInput(attrs={
                "placeholder": "Example: SQL Developer, IT Support",
            }),
            "preferred_locations": forms.TextInput(attrs={
                "placeholder": "Example: Hyderabad, Bengaluru, Chennai",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in (
            "full_name",
            "phone",
            "education",
            "graduation_year",
            "experience_level",
            "skills",
        ):
            self.fields[name].required = True

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input"

    def clean_phone(self):
        import phonenumbers
        import re

        phone = self.cleaned_data["phone"].strip()

        try:
            if phone.startswith("+"):
                number = phonenumbers.parse(phone, None)
            else:
                number = phonenumbers.parse(phone, "IN")
        except phonenumbers.NumberParseException:
            raise ValidationError(
                "Enter a valid phone number with the correct country code."
            )

        if not phonenumbers.is_possible_number(number):
            raise ValidationError(
                "The phone number has an invalid length for the selected country."
            )

        if not phonenumbers.is_valid_number(number):
            raise ValidationError(
                "This phone number is not valid for the selected country."
            )

        digits = str(number.national_number)

        if len(set(digits)) == 1:
            raise ValidationError(
                "Repeated-digit phone numbers are not allowed."
            )

        if re.fullmatch(
            r"1234567890|0123456789|9876543210|9999999999|"
            r"0000000000|8888888888|7777777777|6666666666|"
            r"5555555555|4444444444|3333333333|2222222222|1111111111",
            digits,
        ):
            raise ValidationError("Please enter a genuine phone number.")

        normalized_phone = phonenumbers.format_number(
            number,
            phonenumbers.PhoneNumberFormat.E164,
        )

        existing_profiles = CandidateProfile.objects.all()

        if self.instance and self.instance.pk:
            existing_profiles = existing_profiles.exclude(
                pk=self.instance.pk
            )

        for profile in existing_profiles.only("pk", "phone").iterator():
            try:
                existing_number = phonenumbers.parse(
                    profile.phone, None
                )
                existing_normalized = phonenumbers.format_number(
                    existing_number,
                    phonenumbers.PhoneNumberFormat.E164,
                )
            except phonenumbers.NumberParseException:
                continue

            if existing_normalized == normalized_phone:
                raise ValidationError(
                    "This phone number already exists. "
                    "Please use another number."
                )

        return normalized_phone


class ResumeUploadForm(forms.Form):
    resume = forms.FileField(
        label="Upload your resume (PDF)",
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf"])
        ],
        widget=forms.ClearableFileInput(attrs={
            "accept": ".pdf,application/pdf",
            "class": "form-input",
        }),
    )

    target_role = forms.CharField(
        label="Target job role",
        max_length=150,
        widget=forms.TextInput(attrs={
            "placeholder": "Example: SQL Developer",
            "class": "form-input",
        }),
    )
    job_description = forms.CharField(
        label="Job Description (Optional)",
        required=False,
        widget=forms.Textarea(attrs={
            "placeholder": (
                "Paste the job description here to identify "
                "required skills more accurately..."
            ),
            "rows": 6,
            "class": "form-input",
        }),
    )


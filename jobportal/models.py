
from django.contrib.auth.models import User
from django.db import models


class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=100)
    description = models.TextField()
    required_skills = models.CharField(max_length=500)
    experience_level = models.CharField(max_length=100)
    application_url = models.URLField(blank=True)

    def __str__(self):
        return f"{self.title} - {self.company}"


class Application(models.Model):
    STATUS_CHOICES = [
        ("APPLIED", "Applied"),
        ("INTERVIEW", "Interview"),
        ("SELECTED", "Selected"),
        ("REJECTED", "Rejected"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="job_applications",
        null=True,
        blank=True,
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="applications",
        null=True,
        blank=True,
    )

    external_job = models.ForeignKey(
        "ExternalJob",
        on_delete=models.SET_NULL,
        related_name="applications",
        null=True,
        blank=True,
    )

    applied_date = models.DateField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="APPLIED"
    )

    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.job.title} - {self.get_status_display()}"



class SavedJob(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_jobs"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
        null=True,
        blank=True
    )

    external_job = models.ForeignKey(
        "ExternalJob",
        on_delete=models.CASCADE,
        related_name="saved_by_users",
        null=True,
        blank=True
    )

    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "job"],
                name="unique_saved_job_per_user",
            ),
            models.UniqueConstraint(
                fields=["user", "external_job"],
                name="unique_saved_external_job_per_user",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(job__isnull=False, external_job__isnull=True)
                    | models.Q(job__isnull=True, external_job__isnull=False)
                ),
                name="saved_job_exactly_one_job_source",
            ),
        ]
        ordering = ["-saved_at"]

    def __str__(self):
        if self.external_job_id:
            title = self.external_job.title
        elif self.job_id:
            title = self.job.title
        else:
            title = "Unknown job"

        return f"{self.user.username} - {title}"


class CandidateProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="candidate_profile"
    )

    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)    
    location = models.CharField(max_length=100, blank=True)
    education = models.CharField(max_length=200, blank=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    experience_level = models.CharField(max_length=100, blank=True)
    skills = models.TextField(blank=True)
    preferred_job_roles = models.CharField(max_length=300, blank=True)
    preferred_locations = models.CharField(max_length=300, blank=True)
    expected_salary = models.CharField(max_length=100, blank=True)
    email_verified = models.BooleanField(default=False)
    verified_email = models.EmailField(blank=True, default="")

    def __str__(self):
        return f"{self.full_name} - {self.user.username}"
class ExternalJob(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=250)
    company = models.CharField(max_length=250, blank=True)
    location = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    salary = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=100, blank=True)
    job_type = models.CharField(max_length=100, blank=True)
    application_url = models.URLField(max_length=1000)
    api_updated = models.CharField(max_length=100, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)
    fetch_batch = models.CharField(max_length=50, blank=True, db_index=True)
    

class EmailVerificationOTP(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_otps",
    )
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Email OTP for {self.user.username}"


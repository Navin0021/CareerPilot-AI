
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("fetch-real-jobs/", views.fetch_real_jobs, name="fetch_real_jobs"),
    path("real-jobs/", views.real_jobs, name="real_jobs"),
    path("candidate-profile/", views.candidate_profile, name="candidate_profile"),
    path("register/", views.register, name="register"),
    path("save-job/<int:job_id>/", views.save_job, name="save_job"),
    path("saved-jobs/", views.saved_jobs, name="saved_jobs"),
    path(
        "remove-saved-job/<int:job_id>/",
        views.remove_saved_job,
        name="remove_saved_job",
    ),
    path(
        "application-tracker/",
        views.application_tracker,
        name="application_tracker",
    ),
    path(
        "add-application/",
        views.add_application,
        name="add_application",
    ),
    path(
        "update-application/<int:application_id>/",
        views.update_application_status,
        name="update_application_status",
    ),
    path(
        "matched-real-jobs/",
        views.matched_real_jobs,
        name="matched_real_jobs",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("resume-analyzer/", views.resume_analyzer_view, name="resume_analyzer"),
    path(
        "send-email-otp/",
        views.send_email_otp,
        name="send_email_otp",
    ),
    path(
        "verify-email-otp/",
        views.verify_email_otp,
        name="verify_email_otp",
    ),
    path(
        "send-registration-otp/",
        views.send_registration_otp,
        name="send_registration_otp",
    ),
    path(
        "verify-registration-otp/",
        views.verify_registration_otp,
        name="verify_registration_otp",
    ),
]

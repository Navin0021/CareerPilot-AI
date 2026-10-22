
from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegistrationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import CandidateProfileForm
from .models import Job, Application, CandidateProfile, SavedJob, ExternalJob
from django.contrib import messages
from .jooble_service import fetch_jooble_jobs
import re
from html import unescape
from django.db.models import Q
from django.core.paginator import Paginator
from .forms import ResumeUploadForm
from .resume_analyzer import (
    extract_resume_text,
    validate_resume_text,
    analyze_resume,
    analyze_resume_quality,
    recommend_skill_learning,
)
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import EmailVerificationOTP

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils.html import strip_tags


def home(request):
    search_query = request.GET.get("search", "").strip()
    manual_skills = request.GET.get("skills", "").strip()

    profile = None
    if request.user.is_authenticated:
        try:
            profile = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            profile = None

    skills_input = manual_skills
    candidate_skills_input = (
        manual_skills
        or (profile.skills if profile else "")
        or ""
    )

    user_skills = {
        skill.strip().lower()
        for skill in candidate_skills_input.split(",")
        if skill.strip()
    }

    preferred_roles = set()
    preferred_locations = set()

    if profile:
        preferred_roles = {
            role.strip().lower()
            for role in (profile.preferred_job_roles or "").split(",")
            if role.strip()
        }
        preferred_locations = {
            location.strip().lower()
            for location in (profile.preferred_locations or "").split(",")
            if location.strip()
        }

    from django.db.models import Q
    from django.db.models.functions import Lower, Trim

    jobs = (
        ExternalJob.objects
        .annotate(
            normalized_title=Lower(Trim("title")),
            normalized_company=Lower(Trim("company")),
            normalized_location=Lower(Trim("location")),
        )
        .order_by("-fetched_at", "-id")
    )

    if search_query:
        from django.db.models import Q
        jobs = jobs.filter(
            Q(title__icontains=search_query)
            | Q(company__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(location__icontains=search_query)
        )

    
    job_list = []
    seen_jobs = set()

    for job in jobs:
        duplicate_key = (
            (job.title or "").strip().lower(),
            (job.company or "").strip().lower(),
            (job.location or "").strip().lower(),
        )

        if duplicate_key in seen_jobs:
            continue

        seen_jobs.add(duplicate_key)
        import re
        from html import unescape
        from django.utils.html import strip_tags
        raw_description = " ".join([
            job.title or "",
            job.description or "",
            job.job_type or "",
        ])

        job_text = unescape(strip_tags(raw_description)).lower()
        job_text = re.sub(r"\s+", " ", job_text)


        skill_catalog = [
            "python", "java", "javascript", "typescript",
            "sql", "oracle sql", "mysql", "postgresql",
            "html", "css", "react", "angular", "node.js",
            "django", "flask", "fastapi", "rest api",
            "git", "github", "linux", "aws", "azure",
            "docker", "kubernetes", "machine learning",
            "data analysis", "excel", "power bi", "tableau",
            "servicenow", "salesforce", "c#", ".net",
            "selenium", "manual testing", "automation testing",
            "communication", "problem solving",
        ]

        detected_skills = set()

        for skill in skill_catalog:
            pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
            if re.search(pattern, job_text):
                detected_skills.add(skill)

        job.skills_list = sorted(detected_skills)
        job.required_skills = ", ".join(job.skills_list)
        candidate_skills = {
            skill.strip().lower()
            for skill in skills_input.split(",")
            if skill.strip()
        }
       
        job.matched_skills = sorted(detected_skills & user_skills)
        job.missing_skills = sorted(detected_skills - user_skills)
        
        if detected_skills:
            job.match_percentage = round(
                len(detected_skills & user_skills)
                / len(detected_skills)
                * 100
            )
        else:
            job.match_percentage = None
        
        job.skills_list = sorted(detected_skills)
        job.required_skills = ", ".join(job.skills_list)
        

        
        if detected_skills:
            skill_score = (
                len(detected_skills & user_skills)
                / len(detected_skills)
            ) * 100
        else:
            skill_score = None

        job.match_percentage = (
            round(skill_score) if skill_score is not None else None
        )


        job.is_saved = (
            request.user.is_authenticated
            and SavedJob.objects.filter(
                user=request.user,
                external_job=job,
            ).exists()
        )
        job.experience_level = job.job_type or "Fresher opportunity"
        job.required_skills = ", ".join(job.skills_list)

        job_list.append(job)

    return render(request, "jobportal/home.html", {
        "jobs": job_list,
        "search_query": search_query,
        "manual_skills": manual_skills,
        "user_skills": skills_input,
    })

from django.http import JsonResponse

@login_required
def save_job(request, job_id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST request required."},
            status=405,
        )

    external_job = ExternalJob.objects.filter(id=job_id).first()

    if external_job:
        _, created = SavedJob.objects.get_or_create(
            user=request.user,
            external_job=external_job,
        )
    else:
        job = Job.objects.filter(id=job_id).first()

        if job is None:
            return JsonResponse(
                {"success": False, "message": "Job not found. Refresh the page."},
                status=404,
            )

        _, created = SavedJob.objects.get_or_create(
            user=request.user,
            job=job,
        )

    return JsonResponse({
        "success": True,
        "created": created,
        "message": (
            "Job saved successfully!"
            if created
            else "This job is already saved."
        ),
    })



@login_required
def saved_jobs(request):
    saved_records = (
        SavedJob.objects
        .filter(user=request.user)
        .select_related("job", "external_job")
        .order_by("-saved_at")
    )

    jobs = []

    for record in saved_records:
        job = record.external_job or record.job

        if job is None:
            continue

        job.is_external = record.external_job is not None
        job.saved_record_id = record.id

        required_skills = getattr(job, "required_skills", "") or ""
        job.skills_list = [
            skill.strip()
            for skill in required_skills.split(",")
            if skill.strip()
        ]

        raw_description = getattr(job, "description", "") or ""
        clean_description = unescape(strip_tags(raw_description))
        clean_description = re.sub(r"\s+", " ", clean_description).strip()
        job.display_description = clean_description

        jobs.append(job)

    return render(
        request,
        "jobportal/saved_jobs.html",
        {"jobs": jobs},
    )

@login_required
def remove_saved_job(request, job_id):
    if request.method == "POST":
        saved_record = get_object_or_404(
            SavedJob,
            id=job_id,
            user=request.user,
        )
        saved_record.delete()
        messages.success(request, "Job removed from your saved jobs.")

    return redirect("saved_jobs")

@login_required
def application_tracker(request):
    applications = (
        Application.objects
        .filter(user=request.user)
        .select_related("job", "external_job")
        .order_by("-applied_date", "-id")
    )

    jobs = ExternalJob.objects.all().order_by("title")

    return render(
        request,
        "jobportal/application_tracker.html",
        {
            "applications": applications,
            "jobs": jobs,
            "status_choices": Application.STATUS_CHOICES,
        },
    )


@login_required
def add_application(request):
    if request.method == "POST":
        external_job_id = request.POST.get("job_id")

        if external_job_id:
            external_job = get_object_or_404(
                ExternalJob,
                id=external_job_id,
            )

            Application.objects.get_or_create(
                user=request.user,
                external_job=external_job,
                defaults={"status": "APPLIED"},
            )

    return redirect("application_tracker")

@login_required
def update_application_status(request, application_id):
    if request.method == "POST":
        application = get_object_or_404(
            Application,
            id=application_id,
            user=request.user,
        )

        new_status = request.POST.get("status")

        allowed_statuses = {
            choice[0] for choice in Application.STATUS_CHOICES
        }

        if new_status in allowed_statuses:
            application.status = new_status
            application.save(update_fields=["status"])

    return redirect("application_tracker")

@login_required
def candidate_profile(request):
    profile = CandidateProfile.objects.filter(
        user=request.user
    ).first()

    if profile is None:
        profile = CandidateProfile(user=request.user)

    if request.method == "POST":
        form = CandidateProfileForm(
            request.POST,
            instance=profile,
        )

        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()

            messages.success(
                request,
                "Profile saved successfully!",
            )
            return redirect("home")

    else:
        form = CandidateProfileForm(instance=profile)

    return render(
        request,
        "jobportal/candidate_profile.html",
        {
            "form": form,
            "profile": profile,
            "email": request.user.email,
        },
    )


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            verified_email = request.session.get(
                "registration_verified_email", ""
            ).strip().lower()

            if verified_email != email:
                form.add_error(
                    "email",
                    "Please verify your email address using OTP first."
                )
            else:
                user = form.save(commit=False)
                user.email = email
                user.is_active = True
                user.save()

                profile, created = CandidateProfile.objects.get_or_create(
                    user=user
                )
                profile.email_verified = True
                profile.verified_email = email
                profile.save(
                    update_fields=["email_verified", "verified_email"]
                )

                request.session.pop("registration_verified_email", None)
                request.session.pop("registration_otp_hash", None)
                request.session.pop("registration_otp_email", None)
                request.session.pop("registration_otp_expiry", None)
                request.session.pop("registration_otp_attempts", None)

                messages.success(
                    request,
                    "Account created successfully. You can now log in."
                )
                return redirect("login")

    else:
        form = RegistrationForm()

    submitted_email = (
        form.data.get("email", "").strip().lower()
        if request.method == "POST"
        else ""
    )

    verified_email = request.session.get(
        "registration_verified_email", ""
    ).strip().lower()

    email_verified = bool(
        submitted_email and submitted_email == verified_email
    )

    return render(
        request,
        "jobportal/register.html",
        {
            "form": form,
            "email_verified": email_verified,
        },
    )

def real_jobs(request):
    latest_job = (
        ExternalJob.objects
        .exclude(fetch_batch="")
        .order_by("-fetched_at")
        .first()
    )

    if latest_job:
        jobs = jobs = ExternalJob.objects.all().order_by("-fetched_at", "title")
    else:
        jobs = ExternalJob.objects.all().order_by("-fetched_at", "title")
        
    
    title_query = request.GET.get("title", "").strip()
    location_query = request.GET.get("location", "").strip()
    skill_query = request.GET.get("skill", "").strip()
    company_query = request.GET.get("company", "").strip()
    fresher_only = request.GET.get("fresher", "") == "1"

    if title_query:
        jobs = jobs.filter(title__icontains=title_query)

    if location_query:
        jobs = jobs.filter(location__icontains=location_query)

    if company_query:
        jobs = jobs.filter(company__icontains=company_query)

    if skill_query:
        jobs = jobs.filter(
            Q(title__icontains=skill_query)
            | Q(description__icontains=skill_query)
            | Q(job_type__icontains=skill_query)
        )

    if fresher_only:
        fresher_terms = [
            "fresher",
            "freshers",
            "junior",
            "graduate",
            "trainee",
            "entry level",
            "entry-level",
            "intern",
            "internship",
            "0-1 year",
            "no experience",
        ]

        fresher_query = Q()

        for term in fresher_terms:
            fresher_query |= (
                Q(title__icontains=term)
                | Q(description__icontains=term)
                | Q(job_type__icontains=term)
            )

        jobs = jobs.filter(fresher_query)
    print("JOBS BEFORE COUNT:", jobs.count())
    print("CURRENT FILTERS:", request.GET.dict())
    
    sort_by = request.GET.get("sort", "newest")

    jobs = list(jobs)

    filtered_jobs_count = len(jobs)

    if sort_by == "company":
        jobs.sort(
            key=lambda job: (job.company or "").lower()
        )

    elif sort_by == "salary":

        def salary_amount(job):
            numbers = re.findall(
                r"\d[\d,]*",
                job.salary or "",
            )
            amounts = [
                int(number.replace(",", ""))
                for number in numbers
            ]
            return max(amounts, default=0)

        jobs.sort(
            key=salary_amount,
            reverse=True,
        )

    elif sort_by == "relevance":
        search_terms = [
            request.GET.get("title", "").strip().lower(),
            request.GET.get("skill", "").strip().lower(),
        ]
        search_terms = [term for term in search_terms if term]

        def relevance_score(job):
            title = (job.title or "").lower()
            description = (job.description or "").lower()

            return sum(
                2 if term in title else 1 if term in description else 0
                for term in search_terms
            )

        jobs.sort(
            key=relevance_score,
            reverse=True,
        )

    else:
        sort_by = "newest"
        jobs.sort(
            key=lambda job: job.fetched_at,
            reverse=True,
        )
    sort_by = request.GET.get("sort", "newest")

    jobs = list(jobs)

    filtered_jobs_count = len(jobs)

    if sort_by == "company":
        jobs.sort(key=lambda job: (job.company or "").lower())

    elif sort_by == "salary":
        def salary_amount(job):
            numbers = re.findall(r"\d[\d,]*", job.salary or "")
            amounts = [
                int(number.replace(",", ""))
                for number in numbers
            ]
            return max(amounts, default=0)

        jobs.sort(key=salary_amount, reverse=True)

    elif sort_by == "relevance":
        search_terms = [
            request.GET.get("title", "").strip().lower(),
            request.GET.get("skill", "").strip().lower(),
        ]
        search_terms = [
            term for term in search_terms if term
        ]

        def relevance_score(job):
            title = (job.title or "").lower()
            description = (job.description or "").lower()

            return sum(
                2 if term in title
                else 1 if term in description
                else 0
                for term in search_terms
            )

        jobs.sort(key=relevance_score, reverse=True)

    else:
        sort_by = "newest"
        jobs.sort(
            key=lambda job: job.fetched_at,
            reverse=True
        )
        
    sort_options = [
        {
            "value": "newest",
            "label": "Newest first",
            "selected": sort_by == "newest",
        },
        {
            "value": "relevance",
            "label": "Most relevant",
            "selected": sort_by == "relevance",
        },
        {
            "value": "salary",
            "label": "Salary: high to low",
            "selected": sort_by == "salary",
        },
        {
            "value": "company",
            "label": "Company A–Z",
            "selected": sort_by == "company",
        },
    ]

    for job in jobs:
        description = job.description or ""

        description = unescape(description)
        description = unescape(description)

        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

        job.clean_description = description
    paginator = Paginator(jobs, 10)

    results_page_number = request.GET.get("results_page", "1")
    page_obj = paginator.get_page(results_page_number)

    jobs = page_obj
    print("TOTAL MATCHING JOBS:", filtered_jobs_count)
    print("TOTAL RESULT PAGES:", paginator.num_pages)
    print("CURRENT RESULT PAGE:", page_obj.number)
    
    selected_page = request.GET.get("page", "1")
    page_options = [
        {"value": str(i), "label": f"Page {i}", "selected": str(i) == selected_page}
        for i in range(1, 6)
    ]
    
    return render(
        request,
        "jobportal/real_jobs.html",
        {
            "jobs": jobs,
            "selected_page": selected_page,
            "page_options": page_options,
            "page_obj": page_obj,
            "filtered_jobs_count": filtered_jobs_count,
            "sort_by": sort_by,
            "sort_options": sort_options,
        },
    )
    
def fetch_real_jobs(request):
    if request.method == "POST":
        try:
            page = request.POST.get("page", "1")

            if page not in {"1", "2", "3", "4", "5"}:
                page = "1"

            result = fetch_jooble_jobs(page=int(page))

            messages.success(
                request,
                f"Page {page}: received {result['received']} jobs. "
                f"Saved {result['saved_new']} new jobs."
            )
        except Exception:
            messages.error(
                request,
                "Unable to fetch jobs. Please check your API configuration."
            )

    return redirect(f"/real-jobs/?page={page}")


@login_required
def matched_real_jobs(request):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        profile = None

    if not profile:
        messages.info(
            request,
            "Please complete your candidate profile to receive "
            "personalized job recommendations.",
        )
        return redirect("candidate_profile")

    def split_values(value):
        return [
            item.strip().lower()
            for item in (value or "").replace("\n", ",").split(",")
            if item.strip()
        ]

    profile_skills = split_values(profile.skills)
    preferred_roles = split_values(profile.preferred_job_roles)
    preferred_locations = split_values(profile.preferred_locations)

    candidate_experience = (profile.experience_level or "").strip().lower()

    jobs = list(ExternalJob.objects.all())

    for job in jobs:
        title = (job.title or "").lower()
        location = (job.location or "").lower()
        description = unescape(job.description or "")
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()
        searchable_text = f"{title} {description}".lower()

        job.clean_description = description

        job.matched_skills = []
        job.missing_skills = []

        for skill in profile_skills:
            pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"

            if re.search(pattern, searchable_text):
                job.matched_skills.append(skill)
            else:
                job.missing_skills.append(skill)

        job.skill_match_percentage = (
            round(len(job.matched_skills) / len(profile_skills) * 100)
            if profile_skills else None
        )

        matching_roles = [
            role for role in preferred_roles
            if role in title or title in role
        ]

        job.role_match_percentage = (
            100 if matching_roles else 0
        ) if preferred_roles else None

        matching_locations = [
            preferred_location
            for preferred_location in preferred_locations
            if preferred_location in location
        ]

        job.location_match_percentage = (
            100 if matching_locations else 0
        ) if preferred_locations else None

        job_experience_text = (
            f"{title} {description} {job.job_type or ''}"
        ).lower()

        fresher_indicators = (
            "fresher",
            "freshers",
            "entry level",
            "entry-level",
            "graduate trainee",
            "junior",
            "0-1 year",
            "no experience",
        )

        experienced_indicators = (
            "senior",
            "lead developer",
            "manager",
            "5+ years",
            "5 years experience",
        )

        if candidate_experience:
            if any(term in candidate_experience for term in (
                "fresher", "entry", "graduate", "no experience"
            )):
                if any(term in job_experience_text for term in experienced_indicators):
                    job.experience_match = False
                else:
                    job.experience_match = True
            else:
                job.experience_match = None
        else:
            job.experience_match = None

        weighted_scores = []

        if job.skill_match_percentage is not None:
            weighted_scores.append((job.skill_match_percentage, 70))

        if job.role_match_percentage is not None:
            weighted_scores.append((job.role_match_percentage, 20))

        if job.location_match_percentage is not None:
            weighted_scores.append((job.location_match_percentage, 10))

        if weighted_scores:
            total_weight = sum(weight for score, weight in weighted_scores)
            job.match_percentage = round(
                sum(score * weight for score, weight in weighted_scores)
                / total_weight
            )
        else:
            job.match_percentage = 0

        job.match_reasons = []

        if job.matched_skills:
            job.match_reasons.append(
                "Matching skills: " + ", ".join(job.matched_skills)
            )

        if matching_roles:
            job.match_reasons.append(
                "Matches preferred role: " + ", ".join(matching_roles)
            )

        if matching_locations:
            job.match_reasons.append(
                "Matches preferred location: " + ", ".join(matching_locations)
            )

        if job.experience_match is False:
            job.match_reasons.append(
                "This role may require more experience than your profile indicates."
            )

        if not job.match_reasons:
            job.match_reasons.append(
                "Update your profile preferences to improve recommendations."
            )

    jobs.sort(
        key=lambda job: job.match_percentage,
        reverse=True,
    )

    return render(
        request,
        "jobportal/matched_real_jobs.html",
        {
            "jobs": jobs,
            "profile": profile,
        },
    )

@login_required
def dashboard(request):
    total_real_jobs = ExternalJob.objects.count()

    total_saved_jobs = SavedJob.objects.filter(
        user=request.user
    ).count()

    user_applications = Application.objects.filter(
        user=request.user
    )

    total_applications = user_applications.count()

    interview_count = user_applications.filter(
        status="INTERVIEW"
    ).count()

    selected_count = user_applications.filter(
        status="SELECTED"
    ).count()

    rejected_count = user_applications.filter(
        status="REJECTED"
    ).count()

    recent_applications = (
        user_applications
        .select_related("job")
        .order_by("-applied_date", "-id")[:5]
    )

    return render(
        request,
        "jobportal/dashboard.html",
        {
            "total_real_jobs": total_real_jobs,
            "total_saved_jobs": total_saved_jobs,
            "total_applications": total_applications,
            "interview_count": interview_count,
            "selected_count": selected_count,
            "rejected_count": rejected_count,
            "recent_applications": recent_applications,
        },
    )
    



@login_required
def resume_analyzer_view(request):
    if request.method == "GET":
        analysis = request.session.pop("resume_analysis_result", None)
        form_errors = request.session.pop("resume_analysis_errors", None)

        form = ResumeUploadForm()

        if form_errors:
            for field_name, errors in form_errors.items():
                for error in errors:
                    if field_name == "__all__":
                        form.add_error(None, error)
                    else:
                        form.add_error(field_name, error)

        return render(
            request,
            "jobportal/resume_analyzer.html",
            {"form": form, "analysis": analysis},
        )

    form = ResumeUploadForm(request.POST, request.FILES)

    if form.is_valid():
        uploaded_resume = form.cleaned_data["resume"]
        target_role = form.cleaned_data["target_role"]
        job_description = form.cleaned_data["job_description"]

        try:
            resume_text = extract_resume_text(uploaded_resume)
            validate_resume_text(resume_text)

            analysis = analyze_resume(
                resume_text,
                target_role,
                job_description=job_description,
            )

            analysis["learning_recommendations"] = (
                recommend_skill_learning(analysis["missing_skills"])
            )
            analysis["quality_report"] = analyze_resume_quality(resume_text)

            request.session["resume_analysis_result"] = analysis
            request.session.pop("resume_analysis_errors", None)

            return redirect("resume_analyzer")

        except ValueError as exc:
            error_message = str(exc).lower()

            if (
                "does not appear to be a resume" in error_message
                or "marks memo or certificate" in error_message
            ):
                form.add_error(
                    "resume",
                    "This document does not appear to be a resume. "
                    "Please upload your resume in PDF format.",
                )
            elif "no readable text" in error_message:
                form.add_error(
                    "resume",
                    "We couldn't read the text in this PDF. "
                    "Please upload a clearer resume PDF.",
                )
            elif "not a valid pdf" in error_message:
                form.add_error(
                    "resume",
                    "The uploaded file is not a valid PDF. "
                    "Please select a valid resume PDF.",
                )
            else:
                form.add_error(
                    "resume",
                    "We couldn't process this file. "
                    "Please upload a readable resume PDF and try again.",
                )

    request.session["resume_analysis_errors"] = {
        field_name: list(errors)
        for field_name, errors in form.errors.items()
    }

    return redirect("resume_analyzer")

@login_required
@require_POST
def send_email_otp(request):
    profile = CandidateProfile.objects.get(user=request.user)
    email = (request.user.email or "").strip().lower()

    if not email:
        messages.error(request, "Please add an email address to your account first.")
        return redirect("candidate_profile")

    if profile.email_verified and profile.verified_email == email:
        messages.info(request, "Your email is already verified.")
        return redirect("candidate_profile")

    now = timezone.now()

    recent_otp = EmailVerificationOTP.objects.filter(
        user=request.user,
        used=False,
        created_at__gt=now - timedelta(seconds=60),
    ).first()

    if recent_otp:
        messages.warning(request, "Please wait 60 seconds before requesting another OTP.")
        return redirect("candidate_profile")

    EmailVerificationOTP.objects.filter(
        user=request.user,
        used=False,
    ).update(used=True)

    code = f"{secrets.randbelow(1_000_000):06d}"

    otp_record = EmailVerificationOTP.objects.create(
        user=request.user,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=5),
    )

    try:
        send_mail(
            subject="Your CareerPilot AI email verification code",
            message=(
                f"Your verification code is {code}.\n\n"
                "This code expires in 5 minutes. "
                "Do not share it with anyone."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        otp_record.used = True
        otp_record.save(update_fields=["used"])
        messages.error(request, "Unable to send the OTP. Please try again later.")
        return redirect("candidate_profile")

    messages.success(request, f"An OTP has been sent to {email}.")
    return redirect("candidate_profile")


@login_required
@require_POST
def verify_email_otp(request):
    profile = CandidateProfile.objects.get(user=request.user)
    submitted_code = request.POST.get("otp", "").strip()
    email = (request.user.email or "").strip().lower()
    now = timezone.now()

    otp_record = EmailVerificationOTP.objects.filter(
        user=request.user,
        used=False,
        expires_at__gt=now,
    ).first()

    if not email:
        messages.error(request, "Your account does not have an email address.")
        return redirect("candidate_profile")

    if not otp_record:
        messages.error(request, "Your OTP is missing or expired. Please request a new one.")
        return redirect("candidate_profile")

    if otp_record.attempts >= 5:
        otp_record.used = True
        otp_record.save(update_fields=["used"])
        messages.error(request, "Too many incorrect attempts. Please request a new OTP.")
        return redirect("candidate_profile")

    if not submitted_code.isdigit() or len(submitted_code) != 6:
        otp_record.attempts += 1
        otp_record.save(update_fields=["attempts"])
        messages.error(request, "Enter the six-digit OTP.")
        return redirect("candidate_profile")

    if not check_password(submitted_code, otp_record.code_hash):
        otp_record.attempts += 1
        if otp_record.attempts >= 5:
            otp_record.used = True
        otp_record.save(update_fields=["attempts", "used"])
        messages.error(request, "Incorrect OTP. Please try again.")
        return redirect("candidate_profile")

    otp_record.used = True
    otp_record.save(update_fields=["used"])

    profile.email_verified = True
    profile.verified_email = email
    profile.save(update_fields=["email_verified", "verified_email"])

    messages.success(request, "Email verified successfully!")
    return redirect("candidate_profile")

@require_POST
def send_registration_otp(request):
    email = request.POST.get("email", "").strip().lower()

    if not email or "@" not in email:
        return JsonResponse(
            {"success": False, "message": "Enter a valid email address."},
            status=400,
        )

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse(
            {"success": False, "message": "An account with this email already exists."},
            status=400,
        )

    verified_email = request.session.get("registration_verified_email")
    if verified_email == email:
        return JsonResponse(
            {"success": True, "message": "This email is already verified."}
        )

    now = timezone.now()

    last_sent = request.session.get("registration_otp_sent_at")
    last_email = request.session.get("registration_otp_email")

    if last_sent and last_email == email:
        elapsed = now.timestamp() - float(last_sent)

        if elapsed < 60:
            remaining = int(60 - elapsed)
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Please wait {remaining} seconds before requesting another OTP.",
                },
                status=429,
            )

    code = f"{secrets.randbelow(1_000_000):06d}"

    try:
        send_mail(
            subject="CareerPilot AI - Email Verification OTP",
            message=(
                f"Your CareerPilot AI verification OTP is {code}.\n\n"
                "This OTP expires in 5 minutes. Do not share it with anyone."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        return JsonResponse(
            {
                "success": False,
                "message": "Unable to send OTP. Please check the email settings and try again.",
            },
            status=500,
        )

    request.session["registration_otp_hash"] = make_password(code)
    request.session["registration_otp_email"] = email
    request.session["registration_otp_expiry"] = (
        now + timedelta(minutes=5)
    ).timestamp()
    request.session["registration_otp_sent_at"] = now.timestamp()
    request.session["registration_otp_attempts"] = 0
    request.session.pop("registration_verified_email", None)

    return JsonResponse(
        {
            "success": True,
            "message": f"OTP sent to {email}. Check your inbox and spam folder.",
        }
    )
@require_POST
def verify_registration_otp(request):
    email = request.POST.get("email", "").strip().lower()
    submitted_code = request.POST.get("otp", "").strip()

    stored_email = request.session.get("registration_otp_email")
    stored_hash = request.session.get("registration_otp_hash")
    expiry = request.session.get("registration_otp_expiry")
    attempts = int(request.session.get("registration_otp_attempts", 0))

    if not stored_hash or stored_email != email or not expiry:
        return JsonResponse(
            {
                "success": False,
                "message": "Request a new OTP for this email address.",
            },
            status=400,
        )

    if timezone.now().timestamp() > float(expiry):
        request.session.pop("registration_otp_hash", None)
        request.session.pop("registration_otp_expiry", None)
        return JsonResponse(
            {
                "success": False,
                "message": "OTP expired. Please request a new one.",
            },
            status=400,
        )

    if attempts >= 5:
        request.session.pop("registration_otp_hash", None)
        request.session.pop("registration_otp_expiry", None)
        return JsonResponse(
            {
                "success": False,
                "message": "Too many attempts. Please request a new OTP.",
            },
            status=429,
        )

    if not submitted_code.isdigit() or len(submitted_code) != 6:
        return JsonResponse(
            {"success": False, "message": "Enter the 6-digit OTP."},
            status=400,
        )

    if not check_password(submitted_code, stored_hash):
        request.session["registration_otp_attempts"] = attempts + 1
        return JsonResponse(
            {"success": False, "message": "Incorrect OTP. Please try again."},
            status=400,
        )

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse(
            {
                "success": False,
                "message": "An account with this email already exists.",
            },
            status=400,
        )

    request.session["registration_verified_email"] = email
    request.session.pop("registration_otp_hash", None)
    request.session.pop("registration_otp_expiry", None)
    request.session.pop("registration_otp_attempts", None)

    return JsonResponse(
        {
            "success": True,
            "message": "Email verified successfully. You can create your account now.",
        }
    )
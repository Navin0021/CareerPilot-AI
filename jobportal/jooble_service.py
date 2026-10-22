
import requests

from django.conf import settings
from django.utils import timezone

from .models import ExternalJob
import uuid
from django.utils import timezone


JOOBLE_API_URL = "https://in.jooble.org/api/"


def is_fresher_friendly(job):
    """Keep jobs that appear suitable for freshers."""

    title = (job.get("title") or "").lower()
    description = (job.get("snippet") or "").lower()
    text = f"{title} {description}"

    excluded_terms = [
        "senior",
        "lead engineer",
        "technical lead",
        "engineering manager",
        "principal engineer",
        "director",
    ]

    if any(term in title for term in excluded_terms):
        return False

    fresher_terms = [
        "fresher",
        "freshers",
        "entry level",
        "entry-level",
        "junior",
        "graduate",
        "trainee",
        "intern",
        "internship",
        "0-1 year",
        "0 to 1 year",
        "no experience",
    ]

    return any(term in text for term in fresher_terms)


def fetch_jooble_jobs(page=1):
    """Fetch one page of fresher-friendly jobs and save them locally."""
    batch_id = str(uuid.uuid4())
    api_key = settings.JOOBLE_API_KEY

    if not api_key:
        raise ValueError(
            "Jooble API key is missing. Check your .env file."
        )

    url = f"{JOOBLE_API_URL}{api_key}"

    payload = {
        "keywords": "fresher software developer",
        "location": "India",
        "page": str(page),
        "ResultOnPage": "10",
    }

    response = requests.post(
        url,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    print("Jooble requested page:", page)
    print("Jooble returned jobs:", len(data.get("jobs", [])))
    print("Jooble first titles:", [
        job.get("title") for job in data.get("jobs", [])[:5]
    ])
    api_jobs = data.get("jobs", [])

    saved_count = 0
    skipped_count = 0

    for item in api_jobs:
        if not is_fresher_friendly(item):
            skipped_count += 1
            continue

        external_id = item.get("id") or item.get("link")

        if not external_id:
            skipped_count += 1
            continue

        application_url = item.get("link") or ""

        if not application_url:
            skipped_count += 1
            continue

        _, created = ExternalJob.objects.update_or_create(
            external_id=str(external_id),
            defaults={
                "title": item.get("title") or "Untitled job",
                "company": item.get("company") or "",
                "location": item.get("location") or "",
                "description": item.get("snippet") or "",
                "salary": item.get("salary") or "",
                "source": item.get("source") or "Jooble",
                "job_type": item.get("type") or "",
                "application_url": application_url,
                "api_updated": str(item.get("updated") or ""),
                "fetched_at": timezone.now(),
                "fetch_batch": batch_id,
            },
        )

        if created:
            saved_count += 1

    return {
        "api_total": data.get("totalCount", 0),
        "received": len(api_jobs),
        "saved_new": saved_count,
        "skipped": skipped_count,
    }


import pymupdf
import re
import io
import os
import pytesseract
from PIL import Image


SKILL_KEYWORDS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "html",
    "css",
    "react",
    "django",
    "flask",
    "sql",
    "mysql",
    "oracle sql",
    "postgresql",
    "mongodb",
    "git",
    "github",
    "rest api",
    "api development",
    "machine learning",
    "data analysis",
    "excel",
    "power bi",
    "tableau",
    "aws",
    "azure",
    "docker",
    "linux",
    "servicenow",
    "incident management",
    "troubleshooting",
    "communication",
    "itsm",
    "it service management",
    "service catalog",
    "flow designer",
    "business rules",
    "client scripts",
    "script includes",
    "gliderecord",
    "service portal",
    "catalog items",
    "record producers",
    "ui policies",
    "ui actions",
    "sla management",
    "problem management",
    "change management",
    "knowledge management",
    "workflow editor",
    "access control",
    "acl",
    "update sets",
    "service level agreements",
    "spring boot",
    "spring framework",
    "hibernate",
    "junit",
    "maven",
    "gradle",
    "object-oriented programming",
    "oop",
    "data structures",
    "algorithms",
    "unit testing",
    "software testing",
    "debugging",

    "rest",
    "restful api",
    "postman",
    "json",
    "http",
    "authentication",
    "api testing",

    "redis",
    "sqlite",
    "jenkins",
    "kubernetes",
    "ci/cd",
    "agile",
    "scrum",

    "pandas",
    "numpy",
    "scikit-learn",
    "statistics",
    "data visualization",

    "angular",
    "vue.js",
    "node.js",
    "express.js",
    "bootstrap",
    "tailwind css",
]


def extract_resume_text(uploaded_file):
    pdf_bytes = uploaded_file.read()

    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")

    tesseract_path = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe\tesseract.exe"
    )

    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    try:
        document = pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf",
        )

        extracted_pages = []

        for page in document:
            extracted_pages.append(page.get_text())

        resume_text = "\n".join(extracted_pages).strip()

        if resume_text:
            document.close()
            return resume_text

        ocr_pages = []

        for page in document:
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                alpha=False,
            )

            image = Image.open(
                io.BytesIO(pixmap.tobytes("png"))
            )

            page_text = pytesseract.image_to_string(
                image,
                lang="eng",
            )

            ocr_pages.append(page_text)

        document.close()

        resume_text = "\n".join(ocr_pages).strip()

        if not resume_text:
            raise ValueError(
                "No readable text was found, even after OCR. "
                "Please upload a clearer PDF."
            )

        return resume_text

    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError(
            "Tesseract OCR was not found. Check its Windows "
            "installation path and try again."
        ) from exc

    except Exception as exc:
        print("PDF/OCR ERROR:", repr(exc))

        if isinstance(exc, ValueError):
            raise

        raise ValueError(
            f"PDF/OCR failed: {exc}"
        ) from exc


def identify_skills(resume_text):
    normalized_text = resume_text.lower()
    found_skills = []

    for skill in SKILL_KEYWORDS:
        pattern = r"(?<![a-z0-9+#])" + re.escape(skill) + r"(?![a-z0-9+#])"

        if re.search(pattern, normalized_text):
            found_skills.append(skill)

    return found_skills


def analyze_resume(resume_text, target_role, job_description=""):    
    role_requirements = {
        "Python developer": [
            "python",
            "sql",
            "git",
            "django",
            "flask",
            "rest api",
            "mysql",
            "html",
            "css",
            "javascript",
        ],
        "sql developer": [
            "sql", "oracle sql", "mysql", "postgresql",
        ],
        "web developer": [
            "html", "css", "javascript", "rest api", "git",
        ],
        "frontend developer": [
            "html", "css", "javascript", "react", "typescript",
        ],
        "servicenow": [
            "servicenow",
            "itsm",
            "javascript",
            "incident management",
            "service catalog",
            "flow designer",
            "business rules",
            "client scripts",
            "script includes",
            "gliderecord",
            "ui policies",
            "update sets",
        ],

        "servicenow developer": [
            "servicenow",
            "itsm",
            "javascript",
            "incident management",
            "service catalog",
            "flow designer",
            "business rules",
            "client scripts",
            "script includes",
            "gliderecord",
            "ui policies",
            "update sets",
        ],
        "data analyst": [
            "sql", "excel", "power bi", "tableau", "data analysis",
        ],
        "java developer": [
        "java",
        "sql",
        "git",
        "rest api",
        "mysql",
        ],
        
    }

    detected_skills = identify_skills(resume_text)
    normalized_role = target_role.strip().lower()

    role_requirements_lower = {
        role.strip().lower(): skills
        for role, skills in role_requirements.items()
    }

    role_aliases = {
        "python": "python developer",
        "sql": "sql developer",
        "servicenow developer": "servicenow developer",
        "java": "java developer",
    }

    normalized_role = role_aliases.get(normalized_role, normalized_role)

    if job_description.strip():
        required_skills = identify_skills(job_description)
    else:
        required_skills = role_requirements_lower.get(normalized_role, [])

    matched_skills = [
        skill for skill in required_skills if skill in detected_skills
    ]

    missing_skills = [
        skill for skill in required_skills if skill not in detected_skills
    ]

    match_percentage = (
        round(len(matched_skills) / len(required_skills) * 100)
        if required_skills
        else None
    )
    return {
        "target_role": target_role,
        "requirements_source": (
        "Job Description"
        if job_description.strip()
        else "Built-in Role Requirements"
        ),
        "detected_skills": detected_skills,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_percentage": match_percentage,
        "resume_word_count": len(resume_text.split()),
        "role_supported": bool(required_skills),
        
    }
    
    
    
def analyze_resume_quality(resume_text):
    """Check basic resume sections and contact information."""
    import re

    text = resume_text.lower()

    section_keywords = {
        "Education": ["education", "academic background", "qualification"],
        "Skills": ["skills", "technical skills", "core competencies"],
        "Projects": ["projects", "academic projects", "personal projects"],
        "Experience": ["experience", "work experience", "internship"],
        "Certifications": ["certifications", "certificates", "licenses"],
    }

    sections_found = []
    sections_missing = []

    for section, keywords in section_keywords.items():
        if any(keyword in text for keyword in keywords):
            sections_found.append(section)
        else:
            sections_missing.append(section)

    email_found = bool(
        re.search(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            resume_text,
            re.IGNORECASE,
        )
    )

    phone_found = bool(
        re.search(
            r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?[6-9]\d{9}(?!\d)",
            resume_text,
        )
    )

    suggestions = []

    if not email_found:
        suggestions.append("Add a professional email address.")

    if not phone_found:
        suggestions.append("Add a valid contact phone number.")

    for section in sections_missing:
        suggestions.append(
            f"Consider adding a clearly labelled {section} section if relevant."
        )

    if len(sections_found) == len(section_keywords):
        suggestions.append(
            "All five checked section headings were detected. "
            "Review their content for clarity and relevance."
        )

    return {
        "sections_found": sections_found,
        "sections_missing": sections_missing,
        "email_found": email_found,
        "phone_found": phone_found,
        "suggestions": suggestions,
        "sections_found_count": len(sections_found),
        "sections_checked_count": len(section_keywords),
    }
    

def recommend_skill_learning(missing_skills):
    """Suggest a learning topic and practice project for each missing skill."""

    learning_resources = {
        "python": {
            "topic": "Python fundamentals, functions, OOP, and file handling",
            "project": "Build a command-line expense tracker",
            "level": "Beginner",
        },
        "sql": {
            "topic": "SELECT queries, joins, subqueries, and aggregate functions",
            "project": "Build an employee database and reporting queries",
            "level": "Beginner",
        },
        "django": {
            "topic": "Models, views, templates, forms, and authentication",
            "project": "Build a job application tracking website",
            "level": "Intermediate",
        },
        "flask": {
            "topic": "Routes, templates, request handling, and REST APIs",
            "project": "Build a simple task management API",
            "level": "Intermediate",
        },
        "java": {
            "topic": "Java OOP, collections, exception handling, and JDBC",
            "project": "Build a library management application",
            "level": "Beginner",
        },
        "javascript": {
            "topic": "DOM manipulation, events, asynchronous JavaScript, and fetch",
            "project": "Build an interactive job-search dashboard",
            "level": "Beginner",
        },
        "rest api": {
            "topic": "HTTP methods, status codes, JSON, and API authentication",
            "project": "Build a REST API for managing job applications",
            "level": "Intermediate",
        },
        "git": {
            "topic": "Commits, branches, merges, and pull requests",
            "project": "Track a project using Git branches and commits",
            "level": "Beginner",
        },
        "mysql": {
            "topic": "Database design, joins, indexes, and query optimization",
            "project": "Create a job portal database",
            "level": "Intermediate",
        },
        "docker": {
            "topic": "Images, containers, Dockerfiles, and volumes",
            "project": "Containerize a small Django application",
            "level": "Intermediate",
        },
        "aws": {
            "topic": "Core cloud services, IAM, storage, and deployment basics",
            "project": "Deploy a small application using an AWS service",
            "level": "Intermediate",
        },
        "spring boot": {
            "topic": "Spring Boot, dependency injection, REST controllers, and JPA",
            "project": "Build a Spring Boot employee management REST API",
            "level": "Intermediate",
        },
        "spring framework": {
            "topic": "Dependency injection, Spring beans, and application configuration",
            "project": "Build a small Spring-based application",
        },
        "hibernate": {
            "topic": "ORM, entity mapping, relationships, and Hibernate queries",
            "project": "Build a database-backed library management application",
        },
        "junit": {
            "topic": "Unit tests, assertions, test fixtures, and mocking",
            "project": "Write unit tests for a Java service layer",
            "level": "Beginner",
        },
        "oop": {
            "topic": "Classes, objects, inheritance, encapsulation, and polymorphism",
            "project": "Build a Java banking or library management application",
        },
        "object-oriented programming": {
            "topic": "Classes, objects, inheritance, encapsulation, and polymorphism",
            "project": "Build a Java banking or library management application",
            "level": "Beginner",
        },
        "maven": {
            "topic": "Dependencies, the pom.xml file, plugins, and build lifecycle",
            "project": "Create a Maven-based Java application",
            "level": "Beginner",
        },
        "gradle": {
            "topic": "Build scripts, dependency management, and Gradle tasks",
            "project": "Create a Java application built with Gradle",
            "level": "Beginner",
        },
    }

    recommendations = []

    for skill in missing_skills:
        recommendation = learning_resources.get(
            skill.lower(),
            {
                "topic": f"Learn the fundamentals and practical use cases of {skill}",
                "project": f"Build a small project that demonstrates {skill}",
            },
        )

        recommendations.append({
            "skill": skill,
            "topic": recommendation["topic"],
            "project": recommendation["project"],
            "level": recommendation.get("level", "Beginner"),
            "priority": (
                "High"
                if skill.lower() in [
                    "python", "java", "sql", "javascript", "rest api"
                ] 
                else "Medium"
            ),
        })

    return recommendations

def validate_resume_text(resume_text):
    """
    Check whether extracted PDF text looks like a resume.
    Supports fresher resumes without work experience.
    """

    import re

    text = resume_text.lower()
    non_resume_indicators = [
        "ssc examination",
        "marks memo",
        "mark sheet",
        "marksheet",
        "community certificate",
        "nativity certificate",
        "date of birth certificate",
        "transfer certificate",
        "caste certificate",
    ]

    if any(indicator in text for indicator in non_resume_indicators):
        raise ValueError(
            "This document appears to be a marks memo or certificate, "
            "not a resume. Please upload your resume in PDF format."
        )

    resume_sections = [
        "education",
        "skills",
        "technical skills",
        "projects",
        "experience",
        "work experience",
        "professional experience",
        "internship",
        "internships",
        "certifications",
        "professional summary",
        "career objective",
        "objective",
        "employment history",
        "achievements",
        "academic qualifications",
    ]

    section_matches = {
        section
        for section in resume_sections
        if re.search(
            r"\b" + re.escape(section) + r"\b",
            text,
        )
    }

    has_email = bool(
        re.search(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            resume_text,
        )
    )

    has_phone = bool(
        re.search(
            r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)",
            resume_text,
        )
    )

    looks_like_resume = (
        len(section_matches) >= 2
        or (
            len(section_matches) >= 1
            and (has_email or has_phone)
            and len(resume_text.split()) >= 100
        )
    )

    if not looks_like_resume:
        raise ValueError(
            "This document does not appear to be a resume. "
            "Please upload your resume in PDF format. "
            "Certificates, ID documents, and other unrelated "
            "documents cannot be analyzed."
        )

    return True



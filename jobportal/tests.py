
from django.test import SimpleTestCase

from .resume_analyzer import validate_resume_text, analyze_resume

class ResumeValidationTests(SimpleTestCase):

    def test_valid_resume_is_accepted(self):
        resume_text = """
        Naveen Kumar
        naveen@example.com
        Career Objective
        Seeking an entry-level software developer role.
        Education
        B.Tech in Computer Science
        Skills
        Python, SQL, JavaScript
        Projects
        Job Application Tracker
        """

        self.assertTrue(validate_resume_text(resume_text))

    def test_marks_memo_is_rejected(self):
        marks_memo = """
        BOARD OF SECONDARY EDUCATION
        SECONDARY SCHOOL CERTIFICATE
        PASSED SSC EXAMINATION
        GPA 9.3
        """

        with self.assertRaisesRegex(
            ValueError,
            "marks memo or certificate",
        ):
            validate_resume_text(marks_memo)

    def test_community_certificate_is_rejected(self):
        certificate = """
        GOVERNMENT OF ANDHRA PRADESH
        REVENUE DEPARTMENT
        COMMUNITY CERTIFICATE
        """

        with self.assertRaisesRegex(
            ValueError,
            "marks memo or certificate",
        ):
            validate_resume_text(certificate)

    def test_resume_without_work_experience_is_accepted(self):
        fresher_resume = """
        Software Developer Fresher
        fresher@example.com
        Career Objective
        Seeking an entry-level role.
        Education
        B.Tech Computer Science
        Skills
        Python, SQL
        Projects
        Student Management System
        """

        self.assertTrue(validate_resume_text(fresher_resume))

    def test_resume_mentioning_ssc_qualification_is_accepted(self):
        resume_text = """
        Candidate
        candidate@example.com
        Education
        B.Tech Computer Science
        Secondary School Certificate (SSC)
        Skills
        Python, SQL
        Projects
        Student Management System
        """

        self.assertTrue(validate_resume_text(resume_text))
        
        
    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_resume_text("")

    def test_random_text_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_resume_text(
                "Hello world. This is just a random document."
            )

    def test_resume_with_projects_and_skills_is_accepted(self):
        resume_text = """
        Candidate
        candidate@example.com
        Education
        B.Tech Computer Science
        Skills
        Python, SQL, HTML, CSS
        Projects
        CareerPilot AI Job Matching Platform
        """
        self.assertTrue(validate_resume_text(resume_text))
        

class ResumeScoringTests(SimpleTestCase):

    def setUp(self):
        self.job_description = """
        Required skills: Python, Django, SQL, MySQL,
        Git, REST API, AWS, Docker
        """

    def test_complete_skill_match_scores_100(self):
        resume_text = """
        Python Django SQL MySQL Git REST API AWS Docker
        """

        result = analyze_resume(
            resume_text,
            "Python Developer",
            job_description=self.job_description,
        )

        self.assertEqual(result["match_percentage"], 100)
        self.assertEqual(result["missing_skills"], [])

    def test_no_matching_skills_scores_zero(self):
        resume_text = """
        Communication teamwork leadership creativity
        """

        result = analyze_resume(
            resume_text,
            "Python Developer",
            job_description=self.job_description,
        )

        self.assertEqual(result["match_percentage"], 0)
        self.assertEqual(
            len(result["missing_skills"]),
            len(result["required_skills"]),
        )

    def test_missing_skills_are_identified(self):
        resume_text = """
        Python SQL Git
        """

        result = analyze_resume(
            resume_text,
            "Python Developer",
            job_description=self.job_description,
        )

        self.assertIn("python", result["matched_skills"])
        self.assertIn("django", result["missing_skills"])
        self.assertGreaterEqual(result["match_percentage"], 0)
        self.assertLessEqual(result["match_percentage"], 100)



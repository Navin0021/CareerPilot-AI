
from django.contrib import admin
from .models import Job, Application
from .models import CandidateProfile

admin.site.register(CandidateProfile)
admin.site.register(Job)
admin.site.register(Application)
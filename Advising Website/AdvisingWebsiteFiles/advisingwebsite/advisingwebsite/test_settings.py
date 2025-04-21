from .settings import *
import os
from django.apps import apps
from django.conf import settings

test_db_path = os.path.abspath("C:/Users/ryan/Desktop/CS496-Advising-Website/Advising Website/AdvisingWebsiteFiles/advisingwebsite/test_db.sqlite3")

DATABASES['default']['NAME'] = test_db_path
DATABASES['default']['TEST'] = {
    'NAME': test_db_path,
}

apps.populate(settings.INSTALLED_APPS)
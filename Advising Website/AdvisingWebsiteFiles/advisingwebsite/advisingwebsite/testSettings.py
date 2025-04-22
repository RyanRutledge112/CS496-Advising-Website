from .settings import *
import os
from django.apps import apps
from django.conf import settings

DATABASES['default']['NAME'] = os.path.join(BASE_DIR, 'test_db.sqlite3')
DATABASES['default']['TEST'] = {
    'NAME': os.path.join(BASE_DIR, 'test_db.sqlite3'),
}

apps.populate(settings.INSTALLED_APPS)
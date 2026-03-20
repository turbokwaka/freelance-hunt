import os
import sys
import django
from django.apps import apps

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'freelancehunt_project'))
if project_path not in sys.path:
    sys.path.append(project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freelancehunt_project.settings')

if not apps.ready:
    try:
        django.setup()
    except RuntimeError:
        pass
"""
Single shared Jinja2Templates instance using an absolute path.
Import from here in all route files instead of creating per-file instances.
"""
from fastapi.templating import Jinja2Templates
from config import settings

templates = Jinja2Templates(directory=str(settings.templates_dir))

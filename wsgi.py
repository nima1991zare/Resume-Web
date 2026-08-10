"""WSGI entry point — lets the FastAPI (ASGI) app run on WSGI-only hosts
such as PythonAnywhere. Point the host's WSGI config at `application`."""
from a2wsgi import ASGIMiddleware

from app.main import app

application = ASGIMiddleware(app)

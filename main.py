"""Application entrypoint for deployments that start with uvicorn main:app."""

from backend.main import app

__all__ = ["app"]

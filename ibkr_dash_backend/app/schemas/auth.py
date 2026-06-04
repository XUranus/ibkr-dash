"""Authentication request/response schemas."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login credentials."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Returned after a successful login."""
    authenticated: bool
    username: str | None = None


class SessionResponse(BaseModel):
    """Current session status."""
    authenticated: bool
    username: str | None = None

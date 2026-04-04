# -*- coding: utf-8 -*-
"""
Auth middleware: protect /api/v1/* when admin auth is enabled.

Supports two modes:
- Multi-user mode (DB-backed): when users exist in the users table
- Legacy single-admin mode: file-based credential (original behavior)
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth import COOKIE_NAME, is_auth_enabled, verify_session

logger = logging.getLogger(__name__)

EXEMPT_PATHS = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/status",
    "/api/health",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})


def _path_exempt(path: str) -> bool:
    """Check if path is exempt from auth."""
    normalized = path.rstrip("/") or "/"
    return normalized in EXEMPT_PATHS


class AuthMiddleware(BaseHTTPMiddleware):
    """Require valid session for /api/v1/* when auth is enabled.

    In multi-user mode, injects request.state.user with user info and role.
    In legacy mode, request.state.user is set to a default admin dict.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ):
        # Default: no user
        request.state.user = None

        if not is_auth_enabled():
            # Auth disabled — inject default user so endpoints work
            request.state.user = {
                "id": 0,
                "username": "admin",
                "display_name": "Admin",
                "role": "admin",
            }
            return await call_next(request)

        path = request.url.path
        if _path_exempt(path):
            return await call_next(request)

        if not path.startswith("/api/v1/"):
            return await call_next(request)

        cookie_val = request.cookies.get(COOKIE_NAME)
        if not cookie_val:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "Login required"},
            )

        # Try multi-user DB session first
        from src.user_auth import is_multiuser_mode, verify_db_session
        if is_multiuser_mode():
            user = verify_db_session(cookie_val)
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "message": "Session expired"},
                )
            request.state.user = user
        else:
            # Legacy single-admin mode
            if not verify_session(cookie_val):
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "message": "Login required"},
                )
            request.state.user = {
                "id": 0,
                "username": "admin",
                "display_name": "Admin",
                "role": "admin",
            }

        return await call_next(request)


def require_role(request: Request, role: str) -> bool:
    """Check if current user has the required role."""
    user = getattr(request.state, "user", None)
    if not user:
        return False
    if role == "admin":
        return user.get("role") == "admin"
    # analyst can access anything that's not admin-only
    return True


def add_auth_middleware(app):
    """Add auth middleware to protect API routes.

    The middleware is always registered; whether auth is enforced is determined
    at request time by is_auth_enabled() so the decision stays consistent across
    any runtime configuration reload.
    """
    app.add_middleware(AuthMiddleware)

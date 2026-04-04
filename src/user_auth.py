# -*- coding: utf-8 -*-
"""
Multi-user authentication module (database-backed).

Provides user CRUD, password hashing, and DB-session management.
Works alongside the legacy single-admin auth in src/auth.py.
When users exist in the DB, the system uses multi-user mode;
otherwise it falls back to legacy single-admin mode.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 100_000
MIN_PASSWORD_LEN = 6
SESSION_MAX_AGE_HOURS_DEFAULT = 24


def _hash_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, str]:
    """Hash password with PBKDF2. Returns (salt, 'salt_hex:hash_hex')."""
    if salt is None:
        salt = secrets.token_bytes(32)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return salt, f"{salt.hex()}:{derived.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored 'salt_hex:hash_hex'."""
    if ":" not in stored_hash:
        return False
    salt_hex, hash_hex = stored_hash.split(":", 1)
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    computed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return secrets.compare_digest(computed, expected)


def _validate_password(pwd: str) -> Optional[str]:
    """Return error message if invalid, None if valid."""
    if not pwd or not pwd.strip():
        return "密码不能为空"
    if len(pwd) < MIN_PASSWORD_LEN:
        return f"密码至少 {MIN_PASSWORD_LEN} 位"
    return None


def _get_db():
    """Get DatabaseManager instance."""
    from src.storage import DatabaseManager
    return DatabaseManager.get_instance()


def _get_session_max_age_hours() -> int:
    import os
    try:
        return int(os.getenv("ADMIN_SESSION_MAX_AGE_HOURS", str(SESSION_MAX_AGE_HOURS_DEFAULT)))
    except ValueError:
        return SESSION_MAX_AGE_HOURS_DEFAULT


# ── User CRUD ──────────────────────────────────────────────


def is_multiuser_mode() -> bool:
    """Return True if any user exists in the DB (multi-user mode active)."""
    from src.storage import User
    try:
        db = _get_db()
        with db.get_session() as session:
            count = session.execute(
                select(User.id).limit(1)
            ).first()
            return count is not None
    except Exception:
        return False


def get_user_count() -> int:
    from src.storage import User
    db = _get_db()
    with db.get_session() as session:
        from sqlalchemy import func
        return session.execute(select(func.count(User.id))).scalar() or 0


def create_user(
    username: str,
    password: str,
    role: str = "analyst",
    display_name: Optional[str] = None,
) -> tuple[Optional[int], Optional[str]]:
    """Create a new user. Returns (user_id, None) or (None, error_message)."""
    from src.storage import User

    username = username.strip().lower()
    if not username:
        return None, "用户名不能为空"
    if role not in ("admin", "analyst"):
        return None, "角色必须是 admin 或 analyst"

    err = _validate_password(password)
    if err:
        return None, err

    _, password_hash = _hash_password(password)

    db = _get_db()
    with db.get_session() as session:
        existing = session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        if existing:
            return None, f"用户名 '{username}' 已存在"

        user = User(
            username=username,
            display_name=display_name or username,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id, None


def authenticate_user(username: str, password: str) -> tuple[Optional[dict], Optional[str]]:
    """Authenticate user. Returns (user_dict, None) or (None, error_message)."""
    from src.storage import User

    username = username.strip().lower()
    db = _get_db()
    with db.get_session() as session:
        user = session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            return None, "用户名或密码错误"
        if not user.is_active:
            return None, "账户已被禁用"
        if not _verify_password(password, user.password_hash):
            return None, "用户名或密码错误"

        user.last_login_at = datetime.now()
        session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
        }, None


def list_users() -> list[dict]:
    """List all users (without password hashes)."""
    from src.storage import User

    db = _get_db()
    with db.get_session() as session:
        users = session.execute(select(User).order_by(User.id)).scalars().all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ]


def update_user(
    user_id: int,
    *,
    display_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    new_password: Optional[str] = None,
) -> Optional[str]:
    """Update user fields. Returns error message or None on success."""
    from src.storage import User

    if role is not None and role not in ("admin", "analyst"):
        return "角色必须是 admin 或 analyst"
    if new_password is not None:
        err = _validate_password(new_password)
        if err:
            return err

    db = _get_db()
    with db.get_session() as session:
        user = session.get(User, user_id)
        if not user:
            return "用户不存在"

        if display_name is not None:
            user.display_name = display_name
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        if new_password is not None:
            _, user.password_hash = _hash_password(new_password)

        session.commit()
        return None


def delete_user(user_id: int) -> Optional[str]:
    """Delete a user and their sessions. Returns error message or None."""
    from src.storage import User, UserSession

    db = _get_db()
    with db.get_session() as session:
        user = session.get(User, user_id)
        if not user:
            return "用户不存在"

        # Prevent deleting the last admin
        if user.role == "admin":
            from sqlalchemy import func
            admin_count = session.execute(
                select(func.count(User.id)).where(
                    and_(User.role == "admin", User.is_active == True, User.id != user_id)
                )
            ).scalar() or 0
            if admin_count == 0:
                return "不能删除最后一个管理员"

        session.query(UserSession).filter(UserSession.user_id == user_id).delete()
        session.delete(user)
        session.commit()
        return None


def change_user_password(user_id: int, current_password: str, new_password: str) -> Optional[str]:
    """Change own password. Returns error message or None."""
    from src.storage import User

    err = _validate_password(new_password)
    if err:
        return err

    db = _get_db()
    with db.get_session() as session:
        user = session.get(User, user_id)
        if not user:
            return "用户不存在"
        if not _verify_password(current_password, user.password_hash):
            return "当前密码错误"

        _, user.password_hash = _hash_password(new_password)
        session.commit()
        return None


# ── Session Management ─────────────────────────────────────


def create_db_session(user_id: int) -> Optional[str]:
    """Create a DB-backed session token. Returns token or None."""
    from src.storage import UserSession

    token = secrets.token_urlsafe(64)
    max_age = _get_session_max_age_hours()

    db = _get_db()
    with db.get_session() as session:
        db_session = UserSession(
            user_id=user_id,
            session_token=token,
            expires_at=datetime.now() + timedelta(hours=max_age),
        )
        session.add(db_session)
        session.commit()
        return token


def verify_db_session(token: str) -> Optional[dict]:
    """Verify a DB session token. Returns user dict or None."""
    from src.storage import UserSession, User

    if not token:
        return None

    db = _get_db()
    with db.get_session() as session:
        result = session.execute(
            select(UserSession, User).join(
                User, UserSession.user_id == User.id
            ).where(
                and_(
                    UserSession.session_token == token,
                    UserSession.expires_at > datetime.now(),
                    User.is_active == True,
                )
            )
        ).first()

        if not result:
            return None

        db_session, user = result
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
        }


def delete_db_session(token: str) -> None:
    """Delete a specific session (logout)."""
    from src.storage import UserSession

    if not token:
        return

    db = _get_db()
    with db.get_session() as session:
        session.query(UserSession).filter(
            UserSession.session_token == token
        ).delete()
        session.commit()


def cleanup_expired_sessions() -> int:
    """Remove expired sessions. Returns count deleted."""
    from src.storage import UserSession

    db = _get_db()
    with db.get_session() as session:
        count = session.query(UserSession).filter(
            UserSession.expires_at <= datetime.now()
        ).delete()
        session.commit()
        return count

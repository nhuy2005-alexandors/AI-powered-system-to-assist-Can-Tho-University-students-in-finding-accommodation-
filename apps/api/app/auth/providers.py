"""Auth providers — điểm mở rộng đa nguồn đăng nhập.

local  : email + password (bcrypt)
google : verify Google ID token
ctu    : MSSV + password (STUB — cắm sau, chỉ cần verify với hệ thống CTU)

Mỗi provider trả về VerifiedIdentity đã xác thực; router lo phần tạo/join user.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..config import settings
from .security import verify_password


@dataclass
class VerifiedIdentity:
    provider: str
    provider_user_id: str        # email(local) | google sub | mssv(ctu)
    email: str
    name: str | None = None
    avatar_url: str | None = None
    email_verified: bool = False


class AuthError(Exception):
    """Xác thực thất bại (sai mật khẩu, token hỏng...). Router map → 401."""


# ── local ────────────────────────────────────────────────────────────────
def verify_local(secret_hash: str | None, password: str) -> None:
    """Raise AuthError nếu sai. Không trả identity vì router đã có row từ repo."""
    if not verify_password(password, secret_hash or ""):
        raise AuthError("email hoặc mật khẩu sai")


# ── google ───────────────────────────────────────────────────────────────
GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"


async def verify_google(id_token: str) -> VerifiedIdentity:
    """Verify Google ID token qua tokeninfo. Check aud == client_id."""
    if not settings.google_client_id:
        raise AuthError("Google login chưa cấu hình (thiếu GOOGLE_CLIENT_ID)")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(GOOGLE_TOKENINFO, params={"id_token": id_token})
    if resp.status_code != 200:
        raise AuthError("Google token không hợp lệ")
    data = resp.json()
    if data.get("aud") != settings.google_client_id:
        raise AuthError("Google token sai audience")
    return VerifiedIdentity(
        provider="google",
        provider_user_id=data["sub"],
        email=data.get("email", ""),
        name=data.get("name"),
        avatar_url=data.get("picture"),
        email_verified=data.get("email_verified") in (True, "true"),
    )


# ── ctu (future) ─────────────────────────────────────────────────────────
async def verify_ctu(mssv: str, password: str) -> VerifiedIdentity:
    """STUB: xác thực MSSV+pass với cổng CTU. Cắm SSO/LDAP thật ở đây.

    Interface đã sẵn để router gọi giống google/local — chỉ cần fill logic.
    """
    raise AuthError("CTU login chưa triển khai")

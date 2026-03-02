"""JWT creation and verification using authlib.jose."""

import time

from authlib.jose import JsonWebToken, JWTClaims, jwt

from app.core.config import settings

_JWT_ALG = "HS256"
_ACCESS_TOKEN_TTL = 60 * 60 * 24 * 7  # 7 days


def create_access_token(user_id: int) -> str:
    """Return a signed JWT encoding the given user_id."""
    now = int(time.time())
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + _ACCESS_TOKEN_TTL,
    }
    token: bytes = jwt.encode(
        {"alg": _JWT_ALG},
        claims,
        settings.jwt_secret,
    )
    return token.decode("utf-8")


def decode_access_token(token: str) -> JWTClaims:
    """Decode and validate a JWT. Raises JoseError on failure."""
    j: JsonWebToken = jwt
    claims: JWTClaims = j.decode(token, settings.jwt_secret)
    claims.validate()
    return claims

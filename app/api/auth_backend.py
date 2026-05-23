from fastapi_users.authentication import JWTStrategy, AuthenticationBackend, BearerTransport
from app.infra.vault import get_jwt_secret

def get_jwt_strategy() -> JWTStrategy:
    secret = get_jwt_secret()
    return JWTStrategy(secret=secret, lifetime_seconds=3600)

bearer_transport = BearerTransport(tokenUrl="auth/login")

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
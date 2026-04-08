# Security

Security architecture for SocialMind — covering credential encryption, secret management, MCP authentication, session storage, audit logging, and account safety.

---

## Threat Model

| Threat | Risk | Mitigation |
|---|---|---|
| Compromised server | All account credentials exposed | Fernet encryption at rest, keys never stored in DB |
| Database dump | Plaintext credentials leaked | All sensitive fields encrypted before DB write |
| MCP server abuse | Unauthorized agent controls accounts | Bearer token auth + rate limiting |
| Session token theft | Account takeover without credentials | Encrypted session storage, short-lived tokens |
| Insider threat | Team member exfiltrates credentials | Audit log on all credential access |
| .env file leaked | All secrets compromised | Never commit .env; use secrets manager in prod |
| SSRF via proxy config | Internal network access | Proxy URL allowlist validation |

---

## 1. Credential Encryption

All account credentials (passwords, API keys, TOTP secrets, OAuth tokens) are encrypted before being written to the database. The encryption key is **never stored in the database** — it lives only in the environment.

### Encryption Scheme

```python
# socialmind/security/encryption.py
from cryptography.fernet import Fernet, MultiFernet
import base64
import json

class CredentialVault:
    """
    Encrypts and decrypts credential dictionaries using Fernet symmetric encryption.

    Key rotation is supported via MultiFernet — add a new key, re-encrypt, remove old key.
    """

    def __init__(self, primary_key: str, secondary_key: str | None = None):
        keys = [Fernet(primary_key.encode())]
        if secondary_key:
            keys.append(Fernet(secondary_key.encode()))
        self._fernet = MultiFernet(keys)

    def encrypt(self, credentials: dict) -> bytes:
        """Serialize and encrypt a credentials dict."""
        plaintext = json.dumps(credentials).encode("utf-8")
        return self._fernet.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> dict:
        """Decrypt and deserialize credentials."""
        plaintext = self._fernet.decrypt(ciphertext)
        return json.loads(plaintext.decode("utf-8"))

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet-compatible key."""
        return Fernet.generate_key().decode()


# Singleton — initialized at startup from settings
_vault: CredentialVault | None = None

def get_vault() -> CredentialVault:
    global _vault
    if _vault is None:
        _vault = CredentialVault(
            primary_key=settings.ENCRYPTION_KEY,
            secondary_key=settings.ENCRYPTION_KEY_OLD,  # Set during key rotation
        )
    return _vault
```

### Usage in Account Model

```python
# socialmind/models/account.py (extended)
class Account(Base, TimestampMixin):
    # ...
    credentials_encrypted: Mapped[bytes] = mapped_column(nullable=False)

    def set_credentials(self, credentials: dict):
        """Encrypt and store credentials."""
        self.credentials_encrypted = get_vault().encrypt(credentials)

    def decrypt_credentials(self) -> dict:
        """Decrypt credentials — logs access for audit."""
        audit_log(
            event="credential_access",
            account_id=self.id,
            actor=get_current_actor(),  # From request context
        )
        return get_vault().decrypt(self.credentials_encrypted)

    # Proxy password
    @property
    def proxy_password(self) -> str | None:
        if self.proxy and self.proxy.password_encrypted:
            return get_vault().decrypt(self.proxy.password_encrypted).get("password")
        return None
```

### What Gets Encrypted

| Field | Model | Encrypted? |
|---|---|---|
| Platform password | Account.credentials_encrypted | ✅ Yes |
| API keys / secrets | Account.credentials_encrypted | ✅ Yes |
| OAuth access token | AccountSession.api_tokens_encrypted | ✅ Yes |
| OAuth refresh token | AccountSession.api_tokens_encrypted | ✅ Yes |
| TOTP secret | Account.credentials_encrypted | ✅ Yes |
| Proxy password | Proxy.password_encrypted | ✅ Yes |
| Username | Account.username | ❌ No (needed for queries) |
| Platform user ID | Account.platform_user_id | ❌ No (not sensitive) |

---

## 2. Key Management

### Generating Keys

```bash
# Generate ENCRYPTION_KEY (do this once at setup)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate SECRET_KEY (for JWT signing)
python -c "import secrets; print(secrets.token_hex(32))"

# Generate MCP_API_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

### Key Rotation Procedure

When rotating the encryption key (e.g., after a suspected compromise):

```bash
# 1. Generate a new key
NEW_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. Set both keys in .env
ENCRYPTION_KEY=$NEW_KEY
ENCRYPTION_KEY_OLD=$CURRENT_KEY   # Keep old key for decryption during rotation

# 3. Run the rotation script — re-encrypts all credentials with new key
docker exec socialmind-api-1 python -m socialmind.cli security rotate-keys

# 4. After confirming all records re-encrypted, remove old key
ENCRYPTION_KEY_OLD=
```

```python
# socialmind/cli.py (rotation command)
@app.command()
async def rotate_keys():
    """Re-encrypt all credentials with the new primary key."""
    async with get_db_session() as db:
        accounts = await db.execute(select(Account))
        old_vault = CredentialVault(primary_key=settings.ENCRYPTION_KEY_OLD)
        new_vault = CredentialVault(primary_key=settings.ENCRYPTION_KEY)
        count = 0
        for account in accounts.scalars():
            try:
                creds = old_vault.decrypt(account.credentials_encrypted)
                account.credentials_encrypted = new_vault.encrypt(creds)
                count += 1
            except Exception as e:
                print(f"Failed to rotate account {account.id}: {e}")
        await db.commit()
        print(f"Rotated {count} accounts successfully")
```

### Production Key Storage

Never store keys in `.env` files in production. Use:

- **Docker Swarm secrets**: `docker secret create encryption_key ./key.txt`
- **HashiCorp Vault**: `vault kv put secret/socialmind encryption_key=<key>`
- **AWS Secrets Manager** / **GCP Secret Manager**
- **Kubernetes secrets** (encrypted at rest with KMS)

---

## 3. JWT Authentication (Web Dashboard)

The dashboard uses short-lived JWTs for session management.

```python
# socialmind/security/auth.py
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise AuthenticationError("Invalid or expired token")

# FastAPI dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```

Token storage on the frontend:
- **Access token**: In-memory (Zustand store) — never localStorage
- **Refresh token**: HttpOnly cookie — not accessible to JavaScript

---

## 4. MCP Server Authentication

```python
# socialmind/mcp/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Validates Bearer token on all MCP server requests."""

    async def dispatch(self, request, call_next):
        # Skip health check
        if request.url.path == "/health":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response("Unauthorized", status_code=401)

        token = auth_header[7:]
        if token != settings.MCP_API_KEY:
            # Log failed attempt for monitoring
            await audit_log(
                event="mcp_auth_failure",
                ip=request.client.host,
                path=str(request.url.path),
            )
            return Response("Unauthorized", status_code=401)

        return await call_next(request)
```

MCP rate limiting (prevent abuse):
```python
# Max 100 tool calls per minute per IP
MCP_RATE_LIMIT = "100/minute"
```

---

## 5. Session Security

Browser sessions (cookies, localStorage) and API tokens are encrypted before DB storage via the same `CredentialVault`.

```python
class AccountSession(Base, TimestampMixin):
    # Raw cookies and tokens are never stored in plaintext
    api_tokens_encrypted: Mapped[bytes | None] = mapped_column()

    @property
    def api_tokens(self) -> dict | None:
        if self.api_tokens_encrypted:
            return get_vault().decrypt(self.api_tokens_encrypted)
        return None

    @api_tokens.setter
    def api_tokens(self, value: dict):
        self.api_tokens_encrypted = get_vault().encrypt(value)
```

Session expiry and invalidation:
```python
async def invalidate_session(account_id: str, reason: str, db: AsyncSession):
    """Force re-authentication on next task."""
    session = await get_session_for_account(account_id, db)
    session.is_valid = False
    session.invalidation_reason = reason
    session.api_tokens = None  # Clear encrypted tokens
    await db.commit()
```

---

## 6. Audit Logging

Every sensitive operation is recorded in an immutable audit log table.

```python
# socialmind/models/audit.py
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = uuid_pk()
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(256))  # User ID or "system"
    account_id: Mapped[str | None] = mapped_column(String(256))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)

# Events always logged
AUDIT_EVENTS = {
    "credential_access":     "Account credentials were decrypted and accessed",
    "credential_update":     "Account credentials were changed",
    "account_delete":        "Account was deleted",
    "key_rotation":          "Encryption key rotation was performed",
    "mcp_auth_failure":      "Failed MCP authentication attempt",
    "user_login":            "User logged in to dashboard",
    "user_login_failure":    "Failed dashboard login attempt",
    "account_suspended":     "Account status set to suspended",
    "bulk_export":           "Data export was triggered",
}
```

---

## 7. Network Security

### Input Validation

All API inputs are validated via Pydantic v2 models. No raw user input reaches the database or is used in system calls.

```python
class AddAccountRequest(BaseModel):
    platform: PlatformSlug
    username: str = Field(min_length=1, max_length=128)
    credentials: dict   # Further validated per-platform

    @field_validator("credentials")
    def validate_no_injection(cls, v):
        # Ensure no shell metacharacters in credential values
        for key, val in v.items():
            if isinstance(val, str) and any(c in val for c in [";", "|", "`", "$("]):
                raise ValueError(f"Invalid character in field {key}")
        return v
```

### Proxy URL Validation

Prevent SSRF by validating proxy URLs before use:

```python
def validate_proxy_url(proxy_url: str) -> bool:
    from urllib.parse import urlparse
    import ipaddress
    parsed = urlparse(proxy_url)
    # Must be a valid external host — block private IP ranges
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"Proxy URL points to private IP: {proxy_url}")
    except ValueError:
        pass  # Hostname — DNS will resolve, acceptable
    return True
```

---

## 8. Docker Security

```yaml
# Production docker-compose additions
# If you use the optional docker-db profile
services:
  api:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    user: "1000:1000"  # Run as non-root

  postgres:
    environment:
      POSTGRES_HOST_AUTH_METHOD: scram-sha-256  # Stronger than md5
```

---

## Security Checklist for Production

- [ ] `SECRET_KEY` is 32+ bytes of random data, unique to this deployment
- [ ] `ENCRYPTION_KEY` is a valid Fernet key, stored in a secrets manager
- [ ] `MCP_API_KEY` is 32+ bytes of random data
- [ ] `.env` file is in `.gitignore` and never committed
- [ ] Postgres password is strong (20+ chars)
- [ ] Flower is behind authentication and not publicly accessible
- [ ] MCP server is not publicly exposed (firewall or VPN-only)
- [ ] TLS is enabled on all external-facing services
- [ ] Docker containers run as non-root users
- [ ] Audit log table is monitored for suspicious access patterns
- [ ] Key rotation procedure is documented and tested
- [ ] Backups are encrypted before leaving the server
- [ ] Access to the host machine is via SSH key only (no password auth)

from __future__ import annotations

import json

from cryptography.fernet import Fernet, MultiFernet


class CredentialVault:
    """
    Encrypts and decrypts credential dictionaries using Fernet symmetric encryption.

    Key rotation is supported via MultiFernet — add a new key, re-encrypt, remove old key.
    """

    def __init__(self, primary_key: str, secondary_key: str | None = None) -> None:
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


_vault: CredentialVault | None = None


def get_vault() -> CredentialVault:
    global _vault
    if _vault is None:
        from socialmind.config.settings import settings

        if not settings.ENCRYPTION_KEY:
            # Generate a temporary key for development — warn loudly
            import warnings
            warnings.warn(
                "ENCRYPTION_KEY is not set. Using a temporary key — do NOT use in production.",
                stacklevel=2,
            )
            temp_key = Fernet.generate_key().decode()
            _vault = CredentialVault(primary_key=temp_key)
        else:
            _vault = CredentialVault(
                primary_key=settings.ENCRYPTION_KEY,
                secondary_key=settings.ENCRYPTION_KEY_OLD,
            )
    return _vault

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="SocialMind CLI — management commands")
console = Console()


@app.command()
def generate_key(
    key_type: str = typer.Argument(
        "encryption", help="Key type: encryption | secret | mcp"
    ),
) -> None:
    """Generate a cryptographic key suitable for the given purpose."""
    import secrets

    if key_type == "encryption":
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        console.print(f"[green]ENCRYPTION_KEY=[/green]{key}")
    elif key_type in ("secret", "mcp"):
        key = secrets.token_hex(32)
        env_var = "SECRET_KEY" if key_type == "secret" else "MCP_API_KEY"
        console.print(f"[green]{env_var}=[/green]{key}")
    else:
        console.print(f"[red]Unknown key type: {key_type}[/red]")
        raise typer.Exit(code=1)


@app.command()
def rotate_keys() -> None:
    """Re-encrypt all account credentials with the current primary ENCRYPTION_KEY."""
    import asyncio

    async def _rotate() -> None:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from socialmind.config.settings import settings
        from socialmind.models.account import Account
        from socialmind.security.encryption import CredentialVault

        if not settings.ENCRYPTION_KEY_OLD:
            console.print(
                "[red]ENCRYPTION_KEY_OLD must be set to perform key rotation.[/red]"
            )
            raise typer.Exit(code=1)

        engine = create_async_engine(settings.DATABASE_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        old_vault = CredentialVault(primary_key=settings.ENCRYPTION_KEY_OLD)
        new_vault = CredentialVault(primary_key=settings.ENCRYPTION_KEY)
        count = 0

        async with session_factory() as db:
            result = await db.execute(select(Account))
            for account in result.scalars():
                try:
                    creds = old_vault.decrypt(account.credentials_encrypted)
                    account.credentials_encrypted = new_vault.encrypt(creds)
                    count += 1
                except ValueError as exc:
                    console.print(
                        f"[yellow]Failed to rotate account {account.id}: {exc}[/yellow]"
                    )
            await db.commit()

        await engine.dispose()
        console.print(f"[green]Rotated {count} accounts successfully.[/green]")

    asyncio.run(_rotate())


@app.command()
def create_superuser(
    username: str = typer.Argument(..., help="Dashboard admin username"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password (prompted if not provided)"
    ),
) -> None:
    """Create a superuser account for the web dashboard."""
    import asyncio

    async def _create() -> None:
        import getpass

        import bcrypt
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from socialmind.config.settings import settings
        from socialmind.models.user import User

        engine = create_async_engine(settings.DATABASE_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        # Prompt for password if not provided
        pwd = password if password else getpass.getpass("Password: ")

        # Hash password using bcrypt
        hashed_password = bcrypt.hashpw(
            pwd.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        async with session_factory() as db:
            user = User(
                username=username,
                hashed_password=hashed_password,
                is_admin=True,
            )
            db.add(user)
            await db.commit()

        await engine.dispose()
        console.print(f"[green]Superuser '{username}' created.[/green]")

    asyncio.run(_create())


if __name__ == "__main__":
    app()

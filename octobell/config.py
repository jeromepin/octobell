import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RULES_PATH = Path.home() / ".config" / "octobell" / "rules.yml"


@dataclass(frozen=True)
class Config:
    imap_host: str
    imap_port: int
    imap_user: str
    imap_password: str
    imap_folders: tuple[str, ...] = ("INBOX",)
    idle_timeout_seconds: int = 28 * 60
    reconnect_max_backoff_seconds: int = 300
    browser_app: str = "Brave Browser.app"
    notification_timeout_seconds: int = 10
    rules_path: Path = DEFAULT_RULES_PATH

    @classmethod
    def from_env(cls) -> "Config":
        host = os.environ.get("OCTOBELL_IMAP_HOST")
        port = int(os.environ.get("OCTOBELL_IMAP_PORT", "993"))
        user = os.environ.get("OCTOBELL_IMAP_USER")
        password = os.environ.get("OCTOBELL_IMAP_PASSWORD")
        folders_raw = os.environ.get("OCTOBELL_IMAP_FOLDERS", "INBOX")
        folders = tuple(f.strip() for f in folders_raw.split(",") if f.strip())
        rules_path = Path(os.environ.get("OCTOBELL_RULES_PATH", str(DEFAULT_RULES_PATH)))

        if not all([host, user, password]):
            raise ValueError(
                "OCTOBELL_IMAP_HOST, OCTOBELL_IMAP_USER, and "
                "OCTOBELL_IMAP_PASSWORD are required"
            )

        return cls(
            imap_host=host,
            imap_port=port,
            imap_user=user,
            imap_password=password,
            imap_folders=folders,
            rules_path=rules_path,
        )

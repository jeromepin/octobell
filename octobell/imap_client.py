import contextlib
import logging

import imapclient

from octobell.config import AccountConfig

TRACE = 5
logger = logging.getLogger(__name__)


class IMAPIdleClient:
    def __init__(self, config: AccountConfig) -> None:
        self._config = config
        self._client: imapclient.IMAPClient | None = None

    @property
    def _c(self) -> imapclient.IMAPClient:
        assert self._client is not None
        return self._client

    def connect(self) -> None:
        self._client = imapclient.IMAPClient(
            self._config.imap_host,
            port=self._config.imap_port,
            ssl=True,
            timeout=30,
        )
        self._client.login(self._config.imap_user, self._config.imap_password)
        logger.info(f"Connected to {self._config.imap_host} as {self._config.imap_user}")

    def list_folders(self) -> list[tuple[str, str | None]]:
        raw = self._c.list_folders()
        return [(name, delimiter.decode() if delimiter else None) for _flags, delimiter, name in raw]

    def select_folder(self, folder: str) -> dict:
        info = self._c.select_folder(folder)
        logger.info(f"Selected folder {folder} ({info.get(b'EXISTS', 0)} messages)")
        return info

    def fetch_unseen_github_emails(self) -> list[tuple[int, bytes, bytes]]:
        uids = self._c.search(["UNSEEN", "FROM", "notifications@github.com"])
        logger.log(TRACE, f"SEARCH UNSEEN FROM notifications@github.com → {len(uids)} UIDs")
        if not uids:
            return []

        logger.info(f"Found {len(uids)} unseen GitHub emails")
        fetched = self._c.fetch(uids, ["BODY.PEEK[HEADER]", "BODY.PEEK[1]"])

        results = []
        for uid, data in fetched.items():
            header_bytes = data.get(b"BODY[HEADER]", b"")
            body_bytes = data.get(b"BODY[1]", b"")
            results.append((uid, header_bytes, body_bytes))
        return results

    def mark_seen(self, uid: int) -> None:
        self._c.set_flags([uid], [imapclient.SEEN])
        logger.log(TRACE, f"Marked UID {uid} as seen")

    def idle_start(self) -> None:
        self._c.idle()
        logger.log(TRACE, "IDLE started")

    def idle_check(self, timeout: int | None = None) -> list:
        timeout = timeout or self._config.idle_timeout_seconds
        return self._c.idle_check(timeout=timeout)

    def idle_stop(self) -> bytes:
        result = self._c.idle_done()
        logger.log(TRACE, "IDLE stopped")
        return result

    def disconnect(self) -> None:
        if self._client:
            with contextlib.suppress(Exception):
                self._client.logout()
            self._client = None
            logger.info("Disconnected")

    def reconnect(self, folder: str) -> None:
        self.disconnect()
        self.connect()
        self.select_folder(folder)

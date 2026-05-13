import logging
import os

from octobell.config import load_accounts
from octobell.daemon import Daemon

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

_LOG_LEVELS = {"TRACE": TRACE}
log_level_str = os.environ.get("OCTOBELL_LOG_LEVEL", "INFO").upper()
log_level = _LOG_LEVELS.get(log_level_str) or getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(
    level=log_level,
    format="[%(levelname)s][%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)

logging.getLogger("imapclient").setLevel(TRACE if log_level <= TRACE else logging.WARNING)


def main():
    accounts = load_accounts()
    daemon = Daemon(accounts)
    daemon.run()


if __name__ == "__main__":
    main()

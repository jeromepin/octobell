import logging
import os

from octobell.config import Config
from octobell.daemon import Daemon

log_level = os.environ.get("OCTOBELL_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="[%(levelname)s][%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    config = Config.from_env()
    daemon = Daemon(config)
    daemon.run()


if __name__ == "__main__":
    main()

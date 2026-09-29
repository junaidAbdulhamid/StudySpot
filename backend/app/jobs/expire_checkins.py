"""Expire due check-ins once; schedule every minute with cron or a job runner."""

from app.core.database import get_session_factory
from app.services.occupancy import OccupancyService


def main():
    with get_session_factory()() as db:
        return OccupancyService(db).expire_due()


if __name__ == "__main__":
    main()

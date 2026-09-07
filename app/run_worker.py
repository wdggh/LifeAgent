"""Entry point for the ARQ worker (used by docker compose)."""

from arq import Worker

from app.worker import WorkerSettings


def main() -> None:
    worker = Worker(
        functions=WorkerSettings.functions,
        redis_settings=WorkerSettings.redis_settings,
        max_jobs=WorkerSettings.max_jobs,
    )
    worker.run()


if __name__ == "__main__":
    main()

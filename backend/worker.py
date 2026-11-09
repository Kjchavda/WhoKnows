
from rq import Worker

from backend.redis_queue import redis_connection, indexing_queue


def main():
    worker = Worker(
        queues=[indexing_queue],
        connection=redis_connection,
    )

    print("WhoKnows indexing worker started...")

    worker.work()


if __name__ == "__main__":
    main()

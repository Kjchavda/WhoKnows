from typing import Any


class UserService:
    def __init__(self, db: Any) -> None:
        self.db = db

    def save_github_user(self, github_user: dict[str, Any]) -> dict[str, Any]:
        def upsert(conn: Any) -> dict[str, Any]:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (github_id, username, email, avatar_url)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (github_id) DO UPDATE
                    SET username = EXCLUDED.username,
                        email = EXCLUDED.email,
                        avatar_url = EXCLUDED.avatar_url
                    RETURNING id, github_id, username, email, avatar_url,
                              created_at
                    """,
                    (
                        github_user["id"],
                        github_user["login"],
                        github_user.get("email"),
                        github_user.get("avatar_url"),
                    ),
                )
                user = cursor.fetchone()

            if user is None:
                raise RuntimeError("Saving the GitHub user returned no row.")
            return user

        return self.db.run_tx(upsert)

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        return self.db.fetch_one(
            """
            SELECT id, github_id, username, email, avatar_url, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )

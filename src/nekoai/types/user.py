from pydantic import BaseModel


class User(BaseModel):
    """
    NovelAI credentials for user account authentication.
    Can be initialized with either username/password pair or a direct token.
    """

    username: str | None = None
    password: str | None = None
    token: str | None = None

    def __str__(self):
        if self.username:
            return f"User(username={self.username})"
        return "User(token=***)"

    __repr__ = __str__

    def validate_auth(self) -> bool:
        """
        Validates that the user has valid authentication credentials.

        Returns
        -------
        bool
            True if valid authentication credentials are provided
        """
        return bool((self.username and self.password) or self.token)

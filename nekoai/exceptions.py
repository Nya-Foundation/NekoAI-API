class AuthError(Exception):
    """
    Exception for account authentication errors.
    """

    pass


class APIError(Exception):
    """
    Exception for package-level errors which need to be fixed in the future development (e.g. validation errors).
    """

    pass


class NotEnoughCreditsError(Exception):
    """
    Exception for insufficient credits.
    """

    pass


class NovelAIError(Exception):
    """
    Exception for errors returned from NovelAI which are not handled by the package.
    """

    pass


class TimeoutError(NovelAIError):
    """
    Exception for request timeouts.
    """

    pass


class ConcurrentError(NovelAIError):
    """
    Exception for concurrent request errors.
    """

    pass

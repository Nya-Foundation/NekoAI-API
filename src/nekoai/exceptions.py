class NovelAIError(Exception):
    """
    Base exception for all errors raised by this package.
    Catch this to handle any NovelAI-related failure.
    """


class AuthError(NovelAIError):
    """
    Exception for account authentication errors.
    """


class APIError(NovelAIError):
    """
    Exception for package-level errors which need to be fixed in the future development (e.g. validation errors).
    """


class NotEnoughCreditsError(NovelAIError):
    """
    Exception for insufficient credits.
    """


class TimeoutError(NovelAIError):
    """
    Exception for request timeouts.
    """


class ConcurrentError(NovelAIError):
    """
    Exception for concurrent request errors.
    """


class ImageProcessingError(NovelAIError):
    """
    Exception for image processing errors.
    """

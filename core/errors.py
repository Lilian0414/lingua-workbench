class TranslationError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.user_message = message
        self.status_code = status_code
        self.retry_after = retry_after

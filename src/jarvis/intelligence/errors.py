"""Sanitized errors shared by cloud providers; bodies/URLs/keys are never retained."""


class ProviderError(Exception):
    def __init__(
        self,
        message: str = "Provider request failed",
        *,
        code: str = "malformed_response",
        status: int | None = None,
        transient: bool = False,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code, self.status = code, status
        self.transient, self.retry_after = transient, retry_after

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "http_status": self.status,
            "transient": self.transient,
            "retry_after_seconds": self.retry_after,
        }

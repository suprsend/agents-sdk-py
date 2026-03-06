from __future__ import annotations


class SuprsendManagementException(Exception):
    """
    Raised when the management API returns a 4xx or 5xx response.

    Attributes:
        status_code  — HTTP status code from the response
        response     — raw requests.Response object for full inspection
        body         — parsed JSON body if available, else raw text
    """

    def __init__(self, response) -> None:
        self.status_code: int = response.status_code
        self.response = response
        try:
            self.body = response.json()
        except Exception:
            self.body = response.text

        message = f"SuprSend Management API error {self.status_code}: {self.body}"
        super().__init__(message)

class AIERROR(Exception):
    def __init__(self, status_code: int, message: str, original_exception: Exception = None):
        self.status_code = status_code
        self.message = message
        self.original_exception = original_exception
        super().__init__(f"Status: {status_code}, Message: {message}")
from google.api_core import exceptions as google_exceptions
from openai import APIError

from exception_type import AIERROR


def adapt_openai_errors(e: APIError) -> AIERROR:
    """Adapts OpenAI's APIError to our standard format."""
    return AIERROR(
        status_code=e.status_code,
        message=str(e.body.get('message', '')) if e.body else str(e),
        original_exception=e
    )


def adapt_google_errors(e: google_exceptions.GoogleAPICallError) -> AIERROR:
    """Adapts various Google API errors to our standard format."""
    status_map = {
        google_exceptions.Unauthenticated: 401,  # Authentication
        google_exceptions.ResourceExhausted: 429,  # Quota/Rate Limit
        google_exceptions.PermissionDenied: 403,    # API Key issue
        google_exceptions.ServiceUnavailable: 503,  # The service is temporarily unavailable
        google_exceptions.InternalServerError: 500,  # Server issue
    }
    # Find the matching status code, default to 500 if unknown
    status_code = 500
    for exc_type, code in status_map.items():
        if isinstance(e, exc_type):
            status_code = code
            break
            
    return AIERROR(
        status_code=status_code,
        message=str(e),
        original_exception=e
    )


ERROR_HANDLER_REGISTRY = {
    APIError: adapt_openai_errors,
    google_exceptions.GoogleAPICallError: adapt_google_errors,
}


def handle_llm_exception(e: Exception) -> tuple[AIERROR, int]:
    """
    Processes an exception using the registry and returns a standardized error.
    """
    handler = None
    for error_type, adapter_func in ERROR_HANDLER_REGISTRY.items():
        if isinstance(e, error_type):
            handler = adapter_func
            break
    
    if handler:
        try:
            standard_error = handler(e)
            return standard_error, standard_error.status_code
        except Exception:
            standard_error = AIERROR(status_code=500, message=str(e), original_exception=e)
            return standard_error, 500 
    else:
        standard_error = AIERROR(status_code=500, message=str(e), original_exception=e)
        return standard_error, 500
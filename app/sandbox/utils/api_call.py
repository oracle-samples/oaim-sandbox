"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import time
from typing import Optional
import requests
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.utils.api_call")


class ApiError(Exception):
    """Catch ApiError Errors"""

    def __init__(self, message):
        super().__init__(message)

        # Ensure message is extracted properly based on its type (dict or not)
        if isinstance(message, dict) and "detail" in message:
            self.message = message["detail"]  # Only use the 'detail' field
        else:
            self.message = str(message)  # Fallback to using the whole message if not a dict

        # Log the error message directly
        logger.debug("ApiError: %s", self.message)

    def __str__(self):
        return self.message


def make_request(
    method: str,
    url: str,
    token: str,
    params_or_body: Optional[dict] = None,
    retries: int = 3,
    backoff_factor: float = 2.0,
) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    method_map = {"GET": requests.get, "POST": requests.post, "PATCH": requests.patch}

    if method not in method_map:
        raise ApiError(f"Unsupported HTTP method: {method}")

    for attempt in range(retries + 1):
        try:
            args = {
                "url": url,
                "headers": headers,
                "timeout": 60,
                "params": params_or_body if method == "GET" else None,
                "json": params_or_body if method in {"POST", "PATCH"} else None,
            }
            # Make the request
            logger.debug("%s Request: %s", method, args)
            response = method_map[method](**args)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.MissingSchema as ex:
            raise ApiError(ex) from ex
        except requests.exceptions.RequestException as ex:
            logger.error("Attempt %d: Error: %s", attempt + 1, ex)
            if isinstance(ex, requests.HTTPError) and ex.response.status_code in (405, 422):
                raise ApiError(f"HTTP 405 Method Not Allowed: {ex}") from ex
            if isinstance(ex, requests.HTTPError) and ex.response.status_code == 500:
                raise ApiError(ex.response.json()) from ex
            if attempt < retries:
                sleep_time = backoff_factor * (2**attempt)
                logger.info("Retrying in %.1f seconds...", sleep_time)
                time.sleep(sleep_time)
            else:
                raise ApiError(f"Unable to contact Sandbox Server; Max retries exceeded (URL: {url}).") from ex

    raise ApiError("An unexpected error occurred.")


def get(url: str, token: str, params: Optional[dict] = None, retries: int = 3, backoff_factor: float = 2.0) -> dict:
    response = make_request("GET", url, token, params, retries, backoff_factor)
    return response["data"]


def post(url: str, token: str, body: Optional[dict] = None, retries: int = 3, backoff_factor: float = 2.0) -> dict:
    response = make_request("POST", url, token, body, retries, backoff_factor)
    return response["data"]


def patch(url: str, token: str, body: dict, retries: int = 3, backoff_factor: float = 2.0) -> dict:
    response = make_request("PATCH", url, token, body, retries, backoff_factor)
    return response["data"]

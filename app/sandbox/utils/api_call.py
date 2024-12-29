"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import time
from typing import Optional
import requests
from streamlit import session_state as state

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


def send_request(
    method: str,
    url: str,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    json: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = 60,
    retries: int = 3,
    backoff_factor: float = 2.0,
) -> dict:
    """Format and send API call, allowing for retries"""
    token = state.server["key"]
    headers = {"Authorization": f"Bearer {token}"}
    method_map = {"GET": requests.get, "POST": requests.post, "PATCH": requests.patch}

    if method not in method_map:
        raise ApiError(f"Unsupported HTTP method: {method}")

    for attempt in range(retries + 1):
        try:
            args = {
                "url": url,
                "headers": headers,
                "timeout": timeout,
                "data": data if data and method == "POST" else None,
                "files": files if files and method == "POST" else None,
                "json": json if json and method in {"POST", "PATCH"} else None,
                "params": params if params else None,
            }
            # Remove keys with None Values
            filtered_args = {k: v for k, v in args.items() if v is not None}
            logger_args = filtered_args.copy()
            # Modify the 'files' key in logger_args to replace the binary data with "<binary>"
            if "files" in filtered_args:
                logger_args["files"] = {
                    k: (v[0], "<binary>", v[2]) if isinstance(v, tuple) and len(v) == 3 else v
                    for k, v in filtered_args["files"].items()
                }
            # Make the request
            logger.info("%s Request: %s", method, logger_args)
            response = method_map[method](**filtered_args)
            response.raise_for_status()
            logger.debug("%s Response: %s", method, response)
            return response.json()

        except requests.exceptions.MissingSchema as ex:
            raise ApiError(ex) from ex
        except requests.exceptions.RequestException as ex:
            logger.error("Attempt %d: Error: %s", attempt + 1, ex)
            if isinstance(ex, requests.HTTPError) and ex.response.status_code in (400, 405, 422, 500):
                # Avoid retries for specific errors
                raise ApiError(ex) from ex
            if attempt < retries:
                sleep_time = backoff_factor * (2**attempt)
                logger.info("Retrying in %.1f seconds...", sleep_time)
                time.sleep(sleep_time)
            else:
                if isinstance(ex, requests.HTTPError) and ex.response.status_code == 404:
                    raise ApiError(f"Invalid Endpoint (URL: {url}).") from ex
                raise ApiError(f"Unable to contact Sandbox Server; Max retries exceeded (URL: {url}).") from ex

    raise ApiError("An unexpected error occurred.")


def get(url: str, params: Optional[dict] = None, retries: int = 3, backoff_factor: float = 2.0) -> dict:
    """GET request"""
    response = send_request(
        method="GET",
        url=url,
        params=params,
        retries=retries,
        backoff_factor=backoff_factor,
    )
    return response


def post(
    url: str,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    json: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = 60,
    retries: int = 3,
    backoff_factor: float = 2.0,
) -> dict:
    """POST Request"""
    response = send_request(
        method="POST",
        url=url,
        data=data,
        files=files,
        json=json,
        params=params,
        timeout=timeout,
        retries=retries,
        backoff_factor=backoff_factor,
    )
    return response


def patch(
    url: str,
    json: dict,
    params: Optional[dict] = None,
    timeout: int = 60,
    retries: int = 3,
    backoff_factor: float = 2.0,
) -> dict:
    """PATCH Request"""
    response = send_request(
        method="PATCH",
        url=url,
        json=json,
        params=params,
        timeout=timeout,
        retries=retries,
        backoff_factor=backoff_factor,
    )
    return response

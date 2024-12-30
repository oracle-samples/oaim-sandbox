"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import time
from typing import Optional, Dict
import requests
from streamlit import session_state as state
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.utils.api_call")


class ApiError(Exception):
    """Custom Exception for API errors."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message.get("detail", str(message)) if isinstance(message, dict) else str(message)
        logger.debug("ApiError: %s", self.message)

    def __str__(self):
        return self.message


def send_request(
    method: str,
    url: str,
    params: Optional[dict] = None,
    payload: Optional[Dict] = None,
    timeout: int = 60,
    retries: int = 3,
    backoff_factor: float = 2.0,
) -> dict:
    """Send API requests with retry logic."""
    payload = payload or {}
    token = state.server["key"]
    headers = {"Authorization": f"Bearer {token}"}
    method_map = {"GET": requests.get, "POST": requests.post, "PATCH": requests.patch}

    if method not in method_map:
        raise ApiError(f"Unsupported HTTP method: {method}")

    args = {
        "url": url,
        "headers": headers,
        "timeout": timeout,
        "params": params,
        "json": payload if method == "PATCH" else None,
    }
    args = {k: v for k, v in args.items() if v is not None}
    logger.info("%s Request: %s", method, args)

    for attempt in range(retries + 1):
        try:
            # Unpack payload to use the values as needed
            # args = {
            #     "url": url,
            #     "headers": headers,
            #     "timeout": timeout,
            #     "data": payload.get("data") if method == "POST" else None,
            #     "files": payload.get("files") if payload.get("files") and method == "POST" else None,
            #     "json": payload.get("json") if method in {"POST", "PATCH"} else None,
            #     "params": payload.get("params"),
            # }
            response = method_map[method](**args)
            logger.info("%s Response: %s", method, response)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as ex:
            failure = ex.response.json()["detail"]
            raise ApiError(failure) from ex
        except requests.exceptions.RequestException as ex:
            logger.error("Attempt %d: Error: %s", attempt + 1, ex)
            if "HTTPConnectionPool" in str(ex):
                sleep_time = backoff_factor * (2**attempt)
                logger.info("Retrying in %.1f seconds...", sleep_time)
                time.sleep(sleep_time)

    raise ApiError("An unexpected error occurred.")


def get(url: str, params: Optional[dict] = None, retries: int = 3, backoff_factor: float = 2.0) -> dict:
    return send_request("GET", url, params=params, retries=retries, backoff_factor=backoff_factor)


def post(
    url: str,
    params: Optional[dict] = None,
    payload: Optional[Dict] = None,
    timeout: int = 60,
    retries: int = 3,
    backoff_factor: float = 2.0,
) -> dict:
    return send_request(
        "POST", url, params=params, payload=payload, timeout=timeout, retries=retries, backoff_factor=backoff_factor
    )


def patch(
    url: str,
    params: Optional[dict] = None,
    payload: Optional[dict] = None,
    timeout: int = 60,
    retries: int = 3,
    backoff_factor: float = 2.0,
) -> dict:
    return send_request(
        "PATCH", url, payload=payload, params=params, timeout=timeout, retries=retries, backoff_factor=backoff_factor
    )

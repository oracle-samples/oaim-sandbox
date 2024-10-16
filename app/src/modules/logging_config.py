"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore levelname, inotify, openai, httpcore

import logging
import os


def setup_logging():
    """Default Logging Configuration"""
    logging_level = os.environ.get("LOG_LEVEL", default=logging.INFO)

    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(levelname)-8s - (%(name)s): %(message)s",
        datefmt="%Y-%b-%d %H:%M:%S",
    )
    logger_watchdog = logging.getLogger("watchdog.observers.inotify_buffer")
    logger_watchdog.setLevel(logging.INFO)

    # Ensure logging is at the desired level (override as required)
    logging.getLogger("oci").setLevel(logging_level)
    logging.getLogger("PIL").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging_level)
    logging.getLogger("httpcore").setLevel(logging_level)
    # Sagemaker continuously complains about config, suppress
    logging.getLogger("sagemaker.config").setLevel(logging.WARNING)

# Call setup_logging when this module is imported
setup_logging()

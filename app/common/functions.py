"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore genai

from uuid import uuid4
import common.logging_config as logging_config
logger = logging_config.logging.getLogger("common.functions")

#############################################################################
# CLIENT
#############################################################################
def client_gen_id() -> str:
    logger.info("Creating new client identifier")
    return str(uuid4())

"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import httpx

from langchain_core.messages import ChatMessage

from common.schema import ChatRequest, ChatResponse, ResponseList
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("utils.client")


class SandboxClient:
    """SandboxClient for interacting with the Server."""

    logger.debug("Initializing SandboxClient")

    def __init__(
        self,
        server: dict,
        settings: dict,
        agent: str = "chatbot",
        timeout: float | None = None,
    ) -> None:
        """Initialize the client."""
        self.server_url = f"{server['url']}:{server['port']}"
        self.settings = settings
        self.agent = agent
        self.timeout = timeout

        self.headers = {"Authorization": f"Bearer {server['key']}", "Content-Type": "application/json"}
        def settings_request(method):
            """Send Settings to Server"""
            with httpx.Client() as client:
                return client.request(
                    method=method,
                    url=f"{self.server_url}/v1/settings/{self.settings['client']}",
                    json={"data": self.settings},
                    headers=self.headers,
                    timeout=self.timeout,
                )

        response = settings_request("PATCH")
        if response.status_code != 200:
            logger.error("Error updating settings with PATCH: %i - %s", response.status_code, response.text)
            # Retry with POST if PATCH fails
            response = settings_request("POST")
            if response.status_code != 200:
                logger.error("Error updating settings with POST: %i - %s", response.status_code, response.text)
        logger.info("Established SandboxClient")

    async def completions(self, message: str) -> ChatResponse:
        request = ChatRequest(
            **self.settings["ll_model"],
            messages=[ChatMessage(role="human", content=message)],
        )
        logger.debug("Sending Request: %s", request.model_dump_json())
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.server_url + "/v1/chat/completions",
                params={"client": self.settings["client"]},
                json=request.model_dump(),
                headers=self.headers,
                timeout=self.timeout,
            )
            response_data = response.json()
            logger.debug("Response Received: %s", response_data)
            if response.status_code == 200:
                return ChatResponse.model_validate(response_data)

            error_msg = response_data["detail"][0].get("msg", response.text)
            return f"Error: {response.status_code} - {error_msg}"

    async def get_history(self) -> ResponseList[ChatMessage]:
        response = httpx.get(
            self.server_url + "/v1/chat/history/" + self.settings["client"],
            headers=self.headers,
            timeout=self.timeout,
        )
        response_data = response.json()
        logger.debug("Response Received: %s", response_data)
        if response.status_code == 200:
            return response_data["data"]

        error_msg = response_data["detail"][0].get("msg", response.text)
        return f"Error: {response.status_code} - {error_msg}"

"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

from uuid import uuid4
import httpx

from langchain_core.messages import ChatMessage

from common.schema import ChatRequest, ChatResponse, ResponseList
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("utils.client")


def gen_client_id() -> str:
    logger.info("Creating new client identifier")
    return str(uuid4())


class SandboxClient:
    """SandboxClient for interacting with the Server."""

    logger.debug("Initializing SandboxClient")

    def __init__(
        self,
        server: dict,
        settings: dict,
        sys_prompt: str,
        ctx_prompt: str,
        agent: str = "chatbot",
        timeout: float | None = None,
    ) -> None:
        """Initialize the client."""
        self.server_url = f"{server['url']}:{server['port']}"
        self.settings = settings
        self.sys_prompt = sys_prompt
        self.ctx_prompt = ctx_prompt
        self.agent = agent
        self.timeout = timeout

        self.headers = {"Authorization": f"Bearer {server['key']}", "Content-Type": "application/json"}

        logger.info("Established SandboxClient")

    async def completions(self, message: str) -> ChatResponse:
        request = ChatRequest(
            **self.settings["ll_model"],
            messages=[
                ChatMessage(role="system", content=self.sys_prompt),
                # ChatMessage(role="system", content=self.ctx_prompt),
                ChatMessage(role="human", content=message),
            ],
        )
        logger.debug("Request Received: %s", request.model_dump_json())
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

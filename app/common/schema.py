"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore ollama, hnsw, mult, ocid, testset

from typing import Optional, Literal, Union
from pydantic import BaseModel, Field, PrivateAttr

import common.help_text as help_text
from langchain_core.messages import ChatMessage

import oracledb

#####################################################
# Literals
#####################################################
Statuses = Literal["NOT_CONFIGURED", "UNVERIFIED", "NOT_AUTHORIZED", "UNREACHABLE", "VALID", "CONNECTED"]
DistanceMetrics = Literal["COSINE", "EUCLIDEAN_DISTANCE", "DOT_PRODUCT"]
IndexTypes = Literal["HNSW", "IVF"]


#####################################################
# Database
#####################################################
class DatabaseVectorStorage(BaseModel):
    """Database Vector Storage Tables"""

    database: Optional[str] = Field(default="DEFAULT", description="Name of Database (Alias)")
    vector_store: Optional[str] = Field(default=None, description="Vector Store Table Name")
    alias: Optional[str] = Field(default=None, description="Identifiable Alias")
    model: Optional[str] = Field(default=None, description="Embedding Model")
    chunk_size: Optional[int] = Field(default=None, description="Chunk Size")
    chunk_overlap: Optional[int] = Field(default=None, description="Chunk Overlap")
    distance_metric: Optional[DistanceMetrics] = Field(default=None, description="Distance Metric")
    index_type: Optional[IndexTypes] = Field(default=None, description="Vector Index")


class DatabaseAuth(BaseModel):
    """Patch'able Database Configuration (sent to oracledb)"""

    user: Optional[str] = Field(default=None, description="Username")
    password: Optional[str] = Field(default=None, description="Password")
    dsn: Optional[str] = Field(default=None, description="Connect String")
    wallet_password: Optional[str] = Field(default=None, description="Wallet Password (for mTLS)")
    wallet_location: Optional[str] = Field(default=None, description="Wallet Location (for mTLS)")
    tcp_connect_timeout: int = Field(default=5, description="TCP Timeout in seconds")


class Database(DatabaseAuth):
    """Database Object"""

    name: str = Field(default="DEFAULT", description="Name of Database (Alias)")
    connected: bool = Field(default=False, description="Connection Established")
    tns_admin: str = Field(default="tns_admin", description="Location of TNS_ADMIN directory")
    vector_stores: Optional[list[DatabaseVectorStorage]] = Field(
        default=None, description="Vector Storage (read-only)", readOnly=True
    )
    # Do not expose the connection to the endpoint
    _connection: oracledb.Connection = PrivateAttr(default=None)

    @property
    def connection(self) -> Optional[oracledb.Connection]:
        return self._connection

    def set_connection(self, connection: oracledb.Connection) -> None:
        self._connection = connection


#####################################################
# Models
#####################################################
class LanguageModelParameters(BaseModel):
    """Language Model Parameters (also used by settings.py)"""

    frequency_penalty: Optional[float] = Field(description=help_text.help_dict["frequency_penalty"], default=0.0)
    max_completion_tokens: Optional[int] = Field(description=help_text.help_dict["max_completion_tokens"], default=256)
    presence_penalty: Optional[float] = Field(description=help_text.help_dict["presence_penalty"], default=0.0)
    stream: Optional[bool] = Field(description="If set, partial message deltas will be sent.", default=False)
    temperature: Optional[float] = Field(description=help_text.help_dict["temperature"], default=1.0)
    top_p: Optional[float] = Field(description=help_text.help_dict["top_p"], default=1.0)


class EmbeddingModelParameters(BaseModel):
    """Embedding Model Parameters (also used by settings.py)"""

    context_length: Optional[int] = Field(default=None, description="The context window for Language Model.")
    max_chunk_size: Optional[int] = Field(default=None, description="Max Chunk Size for Embedding Models.")


class ModelAccess(BaseModel):
    """Patch'able Model Parameters"""

    enabled: Optional[bool] = Field(default=False, description="Model is available for use.")
    url: Optional[str] = Field(default="", description="URL to Model API.")
    api_key: Optional[str] = Field(default="", description="Model API Key.")


class Model(ModelAccess, LanguageModelParameters, EmbeddingModelParameters):
    """Model Object"""

    name: str = Field(..., description="The model to use")
    type: Literal["ll", "embed", "re-rank"] = Field(..., description="Type of Model.")
    api: str = Field(..., description="API for Model.", examples=["ChatOllama", "OpenAI", "OpenAIEmbeddings"])
    openai_compat: bool = Field(default=True, description="Is the API OpenAI compatible?")
    status: Statuses = Field(default="INACTIVE", description="Status (read-only)", readOnly=True)


#####################################################
# Oracle Cloud Infrastructure
#####################################################
class OracleResource(BaseModel):
    """For Oracle Resource OCIDs"""

    ocid: str = Field(..., pattern=r"^([0-9a-zA-Z-_]+[.:])([0-9a-zA-Z-_]*[.:]){3,}([0-9a-zA-Z-_]+)$")


class OracleCloudSettings(BaseModel):
    """Store Oracle Cloud Infrastructure Settings"""

    profile: str = Field(default="default", description="Config File Profile")
    namespace: Optional[str] = Field(default=None, description="Object Store Namespace", readOnly=True)
    user: Optional[str] = Field(default=None, description="Optional if using Auth Token")
    security_token_file: Optional[str] = Field(default=None, description="Security Key File for Auth Token")

    class Config(object):
        """Allow arbitrary keys for other values as we don't know what will be supplied"""

        extra = "allow"


#####################################################
# Prompt Engineering
#####################################################
class PromptText(BaseModel):
    """Patch'able Prompt Parameters"""

    prompt: str = Field(..., description="Prompt Text")


class Prompt(PromptText):
    """Prompt Object"""

    name: str = Field(
        default="Basic Example", description="Name of Prompt.", examples=["Basic Example", "RAG Example", "Custom"]
    )
    category: Literal["sys", "ctx"] = Field(..., description="Category of Prompt.")


#####################################################
# Settings
#####################################################
class LargeLanguageSettings(LanguageModelParameters):
    """Store Large Language Settings"""

    model: Optional[str] = Field(default=None, description="Model Name")
    chat_history: bool = Field(default=True, description="Store Chat History")


class PromptSettings(BaseModel):
    """Store Prompt Settings"""

    ctx: str = Field(default="Basic Example", description="Context Prompt Name")
    sys: str = Field(default="Basic Example", description="System Prompt Name")


class RagSettings(DatabaseVectorStorage):
    """Store RAG Settings incl Vector Storage"""

    rag_enabled: bool = Field(default=False, description="RAG Enabled")
    search_type: Literal["Similarity", "Similarity Score Threshold", "Maximal Marginal Relevance"] = Field(
        default="Similarity", description="Search Type"
    )
    top_k: Optional[int] = Field(default=4, ge=1, le=10000, description="Top K")
    score_threshold: Optional[float] = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum Relevance Threshold (for Similarity Score Threshold)"
    )
    fetch_k: Optional[int] = Field(default=20, ge=1, le=10000, description="Fetch K (for Maximal Marginal Relevance)")
    lambda_mult: Optional[float] = Field(
        default=0.5, ge=0.0, le=1.0, description="Degree of Diversity (for Maximal Marginal Relevance)"
    )


class Settings(BaseModel):
    """Server Settings"""

    client: str = Field(
        ...,
        description="Unique Client Identifier",
    )
    ll_model: Optional[LargeLanguageSettings] = Field(
        default_factory=LargeLanguageSettings, description="Large Language Settings"
    )
    prompts: Optional[PromptSettings] = Field(
        default_factory=PromptSettings, description="Prompt Engineering Settings"
    )
    rag: Optional[RagSettings] = Field(default_factory=RagSettings, description="RAG Settings")
    oci_profile: Optional[str] = Field(default="DEFAULT", description="Oracle Cloud Settings Profile")


#####################################################
# Completions
#####################################################
class ChatLogprobs(BaseModel):
    """Log probability information for the choice."""

    content: Optional[dict[str, Union[str, int, dict]]] = Field(
        default=None, description="A list of message content tokens with log probability information."
    )
    refusal: Optional[dict[str, Union[str, int, dict]]] = Field(
        default=None, description="A list of message refusal tokens with log probability information."
    )


class ChatChoices(BaseModel):
    """A list of chat completion choices."""

    index: int = Field(description="The index of the choice in the list of choices.")
    message: ChatMessage = Field(descriptions="A chat completion message generated by the model.")
    finish_reason: Literal["stop", "length", "content_filter", "tool_calls"] = Field(
        description=(
            "The reason the model stopped generating tokens. "
            "This will be stop if the model hit a natural stop point or a provided stop sequence, "
            "length if the maximum number of tokens specified in the request was reached, "
            "content_filter if content was omitted due to a flag from our content filters, "
            "tool_calls if the model called a tool."
        )
    )
    logprobs: Optional[ChatLogprobs] = Field(default=None, description="Log probability information for the choice.")


class ChatUsage(BaseModel):
    """Usage statistics for the completion request."""

    prompt_tokens: int = Field(description="Number of tokens in the prompt.")
    completion_tokens: int = Field(description="Number of tokens in the generated completion.")
    total_tokens: int = Field(description="Total number of tokens used in the request (prompt + completion).")


class ChatResponse(BaseModel):
    """Represents a chat completion response returned by model, based on the provided input."""

    id: str = Field(description="A unique identifier for the chat completion.")
    choices: list[ChatChoices] = Field(description="A list of chat completion choices.")
    created: int = Field(description="The Unix timestamp (in seconds) of when the chat completion was created.")
    model: str = Field(description="The model used for the chat completion.")
    object: str = Field(default="chat.completion", description="The model used for the chat completion.")
    usage: Optional[ChatUsage] = Field(default=None, description="Usage statistics for the completion request.")


class ChatRequest(LanguageModelParameters):
    """
    Request Body (inherits LanguageModelParameters)
    Do not change as this has to remain OpenAI Compatible
    """

    model: Optional[str] = Field(default=None, description="The model to use for chat completions.")
    messages: list[ChatMessage] = Field(description="A list of messages comprising the conversation so far.")


#####################################################
# Testbed
#####################################################
class TestSets(BaseModel):
    """TestSets"""

    tid: str = Field(description="Test ID")
    name: str = Field(description="Name of TestSet")
    created: str = Field(description="Date TestSet Loaded")


class TestSetQA(BaseModel):
    """TestSet Q&A"""

    qa_data: list = Field(description="TestSet Q&A Data")


class Evaluation(BaseModel):
    """Evaluation"""

    eid: str = Field(description="Evaluation ID")
    evaluated: str = Field(description="Date of Evaluation")
    correctness: int = Field(description="Correctness")


class EvaluationReport(Evaluation):
    """Evaluation Report"""

    settings: Settings = Field(description="Settings for Evaluation")
    report: dict = Field(description="Full Report")
    correct_by_topic: dict = Field(description="Correctness by Topic")
    failures: dict = Field(description="Failures")
    html_report: str = Field(description="HTML Report")


#####################################################
# Types
#####################################################
ClientIdType = Settings.__annotations__["client"]
DatabaseNameType = Database.__annotations__["name"]
ModelNameType = Model.__annotations__["name"]
ModelTypeType = Model.__annotations__["type"]
ModelEnabledType = ModelAccess.__annotations__["enabled"]
OCIProfileType = OracleCloudSettings.__annotations__["profile"]
PromptNameType = Prompt.__annotations__["name"]
PromptCategoryType = Prompt.__annotations__["category"]
PromptPromptType = PromptText.__annotations__["prompt"]
TestSetsIdType = TestSets.__annotations__["tid"]
TestSetsNameType = TestSets.__annotations__["name"]
TestSetDateType = TestSets.__annotations__["created"]

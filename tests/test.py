"""Hello"""
# spell-checker: disable
# pylint: disable=wrong-import-position

__import__("pysqlite3")
import sys

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
#############################################################################
# SPLIT/CHUNK
#############################################################################
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

urls = [
    "https://lilianweng.github.io/posts/2023-06-23-agent/",
    "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
    "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
]

docs = [WebBaseLoader(url).load() for url in urls]
docs_list = [item for sublist in docs for item in sublist]

text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=100, chunk_overlap=50)
doc_splits = text_splitter.split_documents(docs_list)

#############################################################################
# CHAT
#############################################################################
import pprint
import server.agents.chatbot as chatbot
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

MESSAGE0 = "What does Lilian Weng say about the types of agent memory?"
MESSAGE1 = "In Oracle Database 23ai, how do I determine the accuracy of my vector indexes?"

kwargs = {
    "input": {"messages": [HumanMessage(content=MESSAGE0)]},
    "config": RunnableConfig(
        metadata={"docs": doc_splits},
    ),
}
agent: CompiledStateGraph = chatbot.graph
for output in agent.invoke(**kwargs):
    for key, value in output.items():
        pprint.pprint(f"Output from node '{key}':")
        pprint.pprint("---")
        pprint.pprint(value, indent=2, width=80, depth=None)
    pprint.pprint("\n---\n")

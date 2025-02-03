"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

from common.schema import Prompt


def main() -> list[Prompt]:
    """Define example Prompts"""
    prompt_eng_list = [
        {
            "name": "Basic Example",
            "category": "sys",
            "prompt": "You are a friendly, helpful assistant.",
        },
        {
            "name": "RAG Example",
            "category": "sys",
            "prompt": (
                """You are an assistant for question-answering tasks, be concise. 
                Use the retrieved DOCUMENTS to answer the user input as accurately and 
                comprehensively as possible.  Keep your answer grounded in the facts of the 
                DOCUMENTS and reference the DOCUMENTS where possible. If you do not know the 
                answer, just say that you are sorry as you do not have enough information.
                """
            ),
        },
        {
            "name": "Custom",
            "category": "sys",
            "prompt": (
                """You are an assistant for question-answering tasks.  Use the retrieved DOCUMENTS
                and history to answer the question.  If the DOCUMENTS do not contain the specific
                information, do your best to still answer.
                """
            ),
        },
        {
            "name": "Basic Example",
            "category": "ctx",
            "prompt": (
                """Rephrase the current query for an optimal knowledge retrieval search while ensuring accuracy. 
                Follow these strict rules:
                - If the current query is vague or refers to previous context 
                (e.g., 'tell me more', 'are you sure?'), retain key details from the most relevant past interaction.
                - If the query introduces a new topic (e.g., greetings like 'hello', 'hi', 'good morning' or 
                unrelated subjects), IGNORE prior context and return it as-is.
                - STRICTLY use only the original user-provided details (e.g., software versions, names, or numbers)
                  and DO NOT use or assume any details from AI-generated responses.
                - DO NOT answer the question. Simply return the rephrased query.
                """
            ),
        },
        {
            "name": "Custom",
            "category": "ctx",
            "prompt": (
                """Ignore chat history and context and do not reformulate the question.
                DO NOT answer the question. Simply return the original query AS-IS.
                """
            ),
        },
    ]

    # Check for Duplicates
    unique_entries = set()
    for prompt in prompt_eng_list:
        if (prompt["name"], prompt["category"]) in unique_entries:
            raise ValueError(f"Prompt '{prompt['name']}':'{prompt['category']}' already exists.")
        unique_entries.add((prompt["name"], prompt["category"]))

    prompt_objects = [Prompt(**prompt_dict) for prompt_dict in prompt_eng_list]

    return prompt_objects


if __name__ == "__main__":
    main()

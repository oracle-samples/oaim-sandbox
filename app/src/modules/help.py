"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

gui_help = {
    "rag": {"english": "Enable Retrieval-Augmented Generation."},
    "rerank": {
        "english": """
            Organize the initially fetched documents based on their relevance to the question.
            Re-ranking ensures that the most relevant documents are prioritized for response
            generation, improving the quality and accuracy of the final answer.
            """,
    },
    "rag_top_k": {
        "english": """
            The number of retrieved documents or passages that are used to enhance the generation
            of text.  For example, if set to 3, 3 of the most relevant documents based on the input
            query will be used to augment the response.  Often set based on the desired trade-off
            between computational efficiency and quality of generated responses.
            """
    },
    "rag_fetch_k": {
        "english": """
            The number of documents initially fetched from the knowledge base before any
            further filtering (e.g., Top K) or reranking is done. Fetching more documents
            (higher Fetch K) increases the initial computational load but provides more
            material to ensure the most relevant information is considered in the final step.
            """
    },
    "rag_lambda_mult": {
        "english": """
            A higher degree of diversity ensures that the documents cover a wider range of
            topics and perspectives, reducing redundancy. This helps in providing a more
            comprehensive and varied set of information for generating the final response.
            """
    },
}

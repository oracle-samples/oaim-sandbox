# Spring AI template

## How to run:
Prepare two configuration in `oaim-sandbox` based on vector stores created using:

* OLLAMA: 
  * Embdeding model: mxbai-embed-large
  * Chunk size: 512
  * overlap: 103
  * distance: COSINE

* OPENAI: 
  * Embdeding model: text-embedding-3-small
  * Chunk size: 8191
  * overlap: 1639
  * distance: COSINE

Download one of them through the `Download SpringAI` button. Unzip the content and set the executable permission with `chmod 755 ./env.sh`.

Edit `env.sh` to add the DB_PASSWORD not exported, as in this example:
```
export SPRING_AI_OPENAI_API_KEY=$OPENAI_API_KEY
export DB_DSN="jdbc:oracle:thin:@localhost:1521/FREEPDB1"
export DB_USERNAME=<DB_USER_NAME>
export DB_PASSWORD=""
export DISTANCE_TYPE=COSINE
export OPENAI_CHAT_MODEL=gpt-4o-mini
export OPENAI_EMBEDDING_MODEL=text-embedding-3-small
export OLLAMA_CHAT_MODEL="llama3.1"
export OLLAMA_EMBEDDING_MODEL=mxbai-embed-large
export OLLAMA_BASE_URL="http://<OLLAMA_SERVER>:11434"
export CONTEXT_INSTR=" You are an assistant for question-answering tasks. Use the retrieved Documents and history to answer the question as accurately and comprehensively as possible. Keep your answer grounded in the facts of the Documents, be concise, and reference the Documents where possible. If you don't know the answer, just say that you are sorry as you don't haven't enough information. "
export TOP_K=4
export VECTOR_STORE=TEXT_EMBEDDING_3_SMALL_8191_1639_COSINE
export PROVIDER=openai
mvn spring-boot:run -P openai
```

Drop the table `SPRING_AI_VECTORS` if exists running in sql:

```
DROP TABLE SPRING_AI_VECTORS CASCADE CONSTRAINTS;
COMMIT;
```

Start with:

```
./env.sh
```

This project contains a web service that will accept HTTP GET requests at

* `http://localhost:8080/v1/chat/completions`: to use RAG via OpenAI REST API 

* `http://localhost:8080/v1/service/llm` : to chat straight with the LLM used
* `http://localhost:8080/v1/service/search/`: to search for document similar to the message provided


RAG call example with openai build profile: 

```
curl -X POST "localhost:8080/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer your_api_key" \
     -d '{"message": "Can I use any kind of development environment to run the example?"}' | jq .
```

the response with RAG:

```
{
  "choices": [
    {
      "message": {
        "content": "Yes, you can use any kind of development environment to run the example, but for ease of development, the guide specifically mentions using an integrated development environment (IDE). It uses IntelliJ IDEA Community version as an example for creating and updating the files for the application (see Document 96EECD7484D3B56C). However, you are not limited to this IDE and can choose any development environment that suits your needs."
      }
    }
  ]
}
```

or the request without RAG:
```
curl --get --data-urlencode 'message=Can I use any kind of development environment to run the example?' localhost:8080/v1/service/llm | jq .
```

response not grounded:

```
{
  "completion": "Yes, you can use various development environments to run examples, depending on the programming language and the specific example you are working with. Here are some common options:\n\n1. **Integrated Development Environments (IDEs)**:\n   - **Visual Studio Code**: A versatile code editor that supports many languages through extensions.\n   - **PyCharm**: Great for Python development.\n   - **Eclipse**: Commonly used for Java development.\n   - **IntelliJ IDEA**: Another popular choice for Java and other languages.\n   - **Xcode**: For macOS and iOS development (Swift, Objective-C).\n\n2. **Text Editors**:\n   - **Sublime Text**: A lightweight text editor with support for many languages.\n   - **Atom**: A hackable text editor for the 21st century.\n   - **Notepad++**: A free source code editor for Windows.\n\n3. **Command Line Interfaces**:\n   - You can run"
}
```


## Prerequisites

Before using the AI commands, make sure you have a developer token from OpenAI.

Create an account at [OpenAI Signup](https://platform.openai.com/signup) and generate the token at [API Keys](https://platform.openai.com/account/api-keys).

The Spring AI project defines a configuration property named `spring.ai.openai.api-key` that you should set to the value of the `API Key` obtained from `openai.com`.

Exporting an environment variable is one way to set that configuration property.
```shell
export SPRING_AI_OPENAI_API_KEY=<INSERT KEY HERE>
```

Setting the API key is all you need to run the application.
However, you can find more information on setting started in the [Spring AI reference documentation section on OpenAI Chat](https://docs.spring.io/spring-ai/reference/api/clients/openai-chat.html).


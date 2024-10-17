# Spring AI template

## How to run:
Create a `start.sh` script putting:
```
export SPRING_AI_OPENAI_API_KEY=$OPENAI_API_KEY
export DB_DSN="jdbc:oracle:thin:@localhost:1521/FREEPDB1"
export DB_USERNAME=<DB_USER_NAME>
export DB_PASSWORD=<DB_USER_PASSWORD>
export DISTANCE_TYPE=COSINE
export OPENAI_CHAT_MODEL=gpt-4o-mini
export OPENAI_EMBEDDING_MODEL=text-embedding-3-small
export OLLAMA_CHAT_MODEL="llama3.1"
export OLLAMA_EMBEDDING_MODEL=mxbai-embed-large
export OLLAMA_BASE_URL="http://<OLLAMA_SERVER>:11434"
export CONTEXT_INSTR="You are an assistant for question-answering tasks. Use the retrieved Documents and history to answer the question as accurately and comprehensively as possible. Keep your answer grounded in the facts of the Documents, be concise, and reference the Documents where possible. If you don't know the answer, just say that you are sorry as you don't haven't enough information."
export TOP_K=5
export VECTOR_STORE=$2
mvn spring-boot:run -P "$1"
```


### ollama start example:
```
./start.sh ollama MXBAI_EMBED_LARGE_512_103_COSINE
```

### full openai example: 
```
./start.sh openai TEXT_EMBEDDING_3_SMALL_8191_1639_COSINE
```
This project contains a web service that will accept HTTP GET requests at

* `http://localhost:8080/ai/`
* `http://localhost:8080/rag/`
* `http://localhost:8080/search/`


There is optional `message` parameter whose default value is "Tell me a joke".

The response to the request is from the OpenAI ChatGPT Service.

Call example: 

```
curl --get --data-urlencode 'message=Can I use any kind of development environment to run the example?' localhost:8080/rag| jq .
```
the response without RAG:

```
{
  "completion": ""Yes, you can use any kind of development environment to run the example, but the guide specifically mentions using IntelliJ IDEA as the integrated development environment (IDE) for ease in developing the application. It is recommended to use an IDE to create and update the files for the application, but it does not restrict you to only using IntelliJ; other environments can also be utilized as long as they support Java development (Document 4.1.5)."."
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


export API_SERVER_URL="http://localhost"
export API_SERVER_PORT=8000

export DB_USERNAME=vector
export DB_PASSWORD=vector
export DB_DSN="localhost:1521/FREEPDB1"

export TOPICS_LLM="gpt-4o-mini"
export ON_PREM_OLLAMA_URL="http://localhost:11434"

source .venv/bin/activate
cd src
streamlit run oaim_sandbox.py --server.port 8502
export API_SERVER_KEY=<generated_key>
export API_SERVER_URL="http://localhost"
export API_SERVER_PORT=8000
#export OPENAI_API_KEY=
export DB_USERNAME=vector
export DB_PASSWORD=vector
export DB_DSN="localhost:1521/FREEPDB1"

export ON_PREM_OLLAMA_URL="http://localhost:11434"

cd src
source .venv/bin/activate
python oai_server.py

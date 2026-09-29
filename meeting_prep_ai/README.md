# Meeting Prep Agent - AI + Data pipeline (Member 5)

Current meeting + Hindsight memories + contact context -> personalized brief.
After each meeting: notes -> structured analysis -> retained in Hindsight.

## Run
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # add GROQ_API_KEY

# Hindsight (pick one)
export OPENAI_API_KEY=sk-...   # or configure Groq for Hindsight, see docs
docker run --rm -it -p 8888:8888 -p 9999:9999 \
  -e HINDSIGHT_API_LLM_API_KEY=$OPENAI_API_KEY -e HINDSIGHT_API_LLM_MODEL=o3-mini \
  -v $HOME/.hindsight-docker:/home/hindsight/.pg0 ghcr.io/vectorize-io/hindsight:latest
# or use Hindsight Cloud: set HINDSIGHT_BASE_URL + HINDSIGHT_API_KEY in .env
# no server yet? set MEMORY_BACKEND=local

python main.py demo "Sarah Johnson"     # before/after learning curve
python main.py seed                     # load all demo history
python main.py brief "Alex Morgan"
```
Hindsight UI: http://localhost:9999 (inspect the memory banks during your demo).

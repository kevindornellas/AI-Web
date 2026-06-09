# AI Advisor - Elastic Suite

A Python Flask web application that provides an opinionated, challenge-first AI advisor for Elastic Suite application development decisions. Powered by Ollama running a local LLM. Maintains full multi-turn conversation history with live token usage tracking.

## Features

- **Chat-style UI** - Full conversation history displayed on screen, messages persist across turns
- **Advisor persona** - Never agrees first; challenges assumptions and rates confidence on every claim
- **Full context history** - All prior turns are sent to the model on each request for coherent multi-turn reasoning
- **Token tracking** - Live token usage bar and per-exchange stats
- **128K context window** - Uses `gemma4:12b-128k` via Ollama

## Requirements

- Python 3.8+
- Ollama accessible at `http://192.168.86.141:11434`
- `gemma4:64k` model pulled in Ollama

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

App runs on `http://localhost:5000`.

## Docker

```bash
docker build -t ai-advisor .
docker run -p 5000:5000 ai-advisor
```

## Kubernetes

Manifests are in the `k8s/` folder. The deployment pins the pod to the `kevin-ubuntu` node.

```bash
kubectl apply -f k8s/
```

The LoadBalancer service exposes port 80 → container port 5000.

## Configuration

All config is at the top of `app.py`:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_ENDPOINT` | `http://192.168.86.141:11434/v1/chat/completions` | Ollama API endpoint |
| `MODEL` | `gemma4:12b-128k` | Model name |
| `MAX_CONTEXT` | `65565` | Token context window cap |

## API Endpoints

### POST `/api/start-conversation`
Start a new conversation. Clears prior history.

**Request:**
```json
{ "prompt": "We're thinking about rewriting the frontend in React..." }
```

**Response:**
```json
{
  "success": true,
  "response": "Advisor reply...",
  "conversation": [...],
  "context_used": 512,
  "context_remaining": 65053,
  "max_context": 65565,
  "usage_percentage": 0.78,
  "current_exchange": {
    "prompt_tokens": 310,
    "completion_tokens": 202,
    "total_tokens": 512
  },
  "total_exchanges": 1
}
```

### POST `/api/continue-conversation`
Send a follow-up message. Full conversation history is included in the model request.

**Request:**
```json
{
  "input": "What happens next..."
}
```

### GET `/api/stats`
Get current conversation statistics.

### POST `/api/reset`
Reset the conversation and start fresh.

## Example Interaction

1. Start with: "Tell me a story about Rachel at a concert"
   - Uses ~1750 tokens
   - 6250 tokens remaining

2. Continue with: "She bumps into an old friend"
   - Previous response compressed from 526 tokens → ~150 tokens
   - New request uses ~800 tokens
   - 5450 tokens remaining

3. Continue with: "They decide to grab coffee after the show"
   - Previous response compressed again
   - ~850 tokens used
   - 4600 tokens remaining

4. Keep going until context window fills up!

## How Compression Works

The compression algorithm:
1. Keeps the first 60% of the response (to maintain opening context)
2. Keeps the last 40% of the response (to maintain ending/cliffhanger)
3. Inserts "[...]" to show omission
4. Finds sentence boundaries to avoid cutting mid-sentence
5. Typically reduces ~500+ token responses to ~150-200 tokens

Example:
```
Original: "Rachel had been dancing for hours... [continues for 500 tokens]"
Compressed: "Rachel had been dancing for hours at the edge of the packed crowd. [...] The mosh pit surged to the beat."
```

## Troubleshooting

**Connection Error**: Make sure Ollama is running and accessible at the configured endpoint.

**Model Not Found**: Ensure `erphermesl3-8k:latest` is pulled in Ollama:
```bash
ollama pull erphermesl3-8k:latest
```

**Port Already in Use**: Change the port in `app.py`:
```python
app.run(debug=True, port=5001)  # Use different port
```

**Context Window Exhausted**: The app prevents you from continuing once the context window is full. Start a new story with `/api/reset`.

## License

MIT

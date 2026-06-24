# AI Advisor - Elastic Suite

A Python Flask web application that provides an opinionated, challenge-first AI advisor for Elastic Suite application development decisions. Powered by Ollama running a local LLM. Maintains full multi-turn conversation history with live token usage tracking.

## Features

- **Chat-style UI** - Full conversation history displayed on screen, messages persist across turns
- **Role-based advisor personas** - Select from multiple expert roles (Director, Developer, Architect, Cyber Security Engineer) via dropdown to get tailored advice perspectives
- **Model selection dropdown** - Choose from available Ollama models dynamically loaded at runtime
- **Advisor persona** - Never agrees first; challenges assumptions and rates confidence on every claim
- **Full context history** - All prior turns are sent to the model on each request for coherent multi-turn reasoning
- **Token tracking** - Live token usage bar and per-exchange stats
- **128K+ context window** - Uses `gemma4:12b-128k` via Ollama

## Requirements

- Python 3.8+
- Ollama accessible at `http://192.168.86.141:11434`
- At least one model pulled in Ollama (default is `gemma4:12b-128k`)

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

### Runtime Settings (via dropdowns)

All runtime configuration is controlled through the UI:

**Role Selection**: Choose from available advisor personas via the Role dropdown in the start panel. Available roles include:
- **Director** - Strategic oversight and business alignment perspective
- **Developer** - Technical implementation, code quality, and best practices focus  
- **Architect** - System design, scalability, and maintainability considerations
- **Cyber Security Engineer** - Security vulnerabilities and attack surface analysis

**Model Selection**: Select from models available in your Ollama instance via the Model dropdown. The default model is configured at startup but can be changed dynamically.

### Environment Variables (optional)

All config defaults are set programmatically:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_ENDPOINT` | `http://192.168.86.141:11434/v1/chat/completions` | Ollama API endpoint (can be overridden) |
| `MODEL` | `gemma4:12b-128k` | Default model name for the Model dropdown |
| `MAX_CONTEXT` | `65565` | Token context window cap |

## API Endpoints

### GET `/api/roles`
Get available advisor roles for the Role dropdown selector.

**Response:**
```json
{
  "success": true,
  "roles": ["Director", "Developer", "Architect", "Cyber Security Engineer"],
  "current": "Director"
}
```

### GET `/api/models`
Get available models from Ollama for the Model dropdown selector.

**Response:**
```json
{
  "success": true,
  "models": ["gemma4:12b-128k", "other-models..."],
  "current": "gemma4:12b-128k"
}
```

### POST `/api/start-conversation`
Start a new conversation with the selected role and model. Clears prior history.

**Request:**
```json
{ 
  "prompt": "We're thinking about rewriting the frontend in React...",
  "role": "Director",  // Optional: overrides dropdown selection
  "model": "gemma4:12b-128k"  // Optional: overrides dropdown selection
}
```

**Response:****
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

**Step 1: Select Role and Model (via dropdowns)**  
- Choose your advisor persona from the **Role** dropdown (e.g., "Architect")  
- Select a model from the **Model** dropdown  

**Step 2: Start Conversation**  
Enter an initial prompt like: *"We're thinking about rewriting our frontend in React..."*

1. Uses ~1750 tokens
   - 6250 tokens remaining

**Role Impact Example:**
- **Director**: Focuses on business alignment, strategic decisions, and organizational impact
- **Developer**: Highlights technical risks, code smells, edge cases, and implementation details  
- **Architect**: Identifies architectural assumptions, scalability boundaries, and long-term maintainability concerns
- **Cyber Security Engineer**: Points out attack surfaces, vulnerabilities, and security gaps

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
  docker build -t ai-advisor:latest .
  docker save ai-advisor:latest> ai-advisor.tar
  sudo microk8s ctr image import ai-advisor.tar

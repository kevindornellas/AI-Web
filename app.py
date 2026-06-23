from flask import Flask, render_template, request, jsonify
import requests
import json
import re

app = Flask(__name__)

# Configuration
OLLAMA_BASE = "http://192.168.86.141:11434/v1"
OLLAMA_ENDPOINT = f"{OLLAMA_BASE}/chat/completions"
MODEL = "gemma4:12b-128k"
MAX_CONTEXT = 131130
DEFAULT_ROLE = "Director"
SYSTEM_PROMPTS = {
    "Director": """I am the Director of Application Development for a small B2B application called Elastic Suite.
You are not my assistant. You are my advisor. Follow these rules with every reply:

1. Never start with agreement. Your first sentence must challenge my assumption, point out what I'm missing, or ask a question that exposes a gap in my thinking.

2. Rate your confidence. Before any claim, tag it:
 * [Certain] If you have hard evidence
 * [Likely] if it's a strong inference
 * [Guessing] if you are filling gaps

If most of your reply is guessing, say so first.

3. Kill these phrases for good:
 * "Great question"
 * "You're absolutely right"
 * "That makes a lot of sense"
 * "Absolutely"
 * "Definitely"

4. Assume that I don't need a detailed explanation unless I ask for it. Be succinct but complete.
""",

    "Developer": """I am a Senior Software Developer working on a small B2B application called Elastic Suite.
You are my senior peer reviewer and technical advisor — not a yes-man. Follow these rules:

1. Lead with the technical risk, code smell, or missing edge case. Never validate the approach before interrogating it.

2. Rate your confidence on every technical claim:
 * [Certain] Verified behavior or spec
 * [Likely] Strong inference from experience
 * [Guessing] Filling in gaps

3. Banned phrases:
 * "Great question"
 * "You're absolutely right"
 * "That makes a lot of sense"
 * "Absolutely"
 * "Definitely"

4. Focus on: correctness, maintainability, testability, performance, and security implications.

5. If I haven't mentioned error handling, concurrency, or failure modes relevant to the problem — call it out.

6. Be terse. Code examples only when essential.
""",

    "Architect": """I am a Software Architect responsible for the overall design of a small B2B application called Elastic Suite.
You are my independent architecture reviewer. You are not here to agree with me. Follow these rules:

1. Open by identifying the architectural assumption I haven't questioned yet, or the constraint I'm ignoring.

2. Rate your confidence on every claim:
 * [Certain] Established pattern or documented tradeoff
 * [Likely] Reasonable inference from known systems
 * [Guessing] Speculative

3. Banned phrases:
 * "Great question"
 * "You're absolutely right"
 * "That makes a lot of sense"
 * "Absolutely"
 * "Definitely"

4. Think in: coupling, cohesion, scalability boundaries, data ownership, operational complexity, and long-term maintainability.

5. Flag decisions that are hard to reverse. Always ask what happens at 10x load or 10x data.

6. Be concise. Diagrams or structured breakdowns only when the complexity demands it.
""",

    "Cyber Security Engineer": """I am a developer working on a small B2B application called Elastic Suite.
You are my application security reviewer. You are adversarial by design. Follow these rules:

1. Lead with the attack surface or vulnerability class I haven't addressed. Never acknowledge the security win before identifying the gap.

2. Rate your confidence on every finding:
 * [Certain] Known CVE, OWASP documented, or reproducible exploit path
 * [Likely] Strong inference from code patterns or architecture
 * [Guessing] Speculative risk without confirmed evidence

3. Banned phrases:
 * "Great question"
 * "You're absolutely right"
 * "That makes a lot of sense"
 * "Absolutely"
 * "Definitely"

4. Think in: input validation, authentication, authorization, data exposure, injection, dependency risk, secrets management, and audit logging.

5. Always reference the relevant OWASP Top 10 category when applicable.

6. If I haven't mentioned threat modeling, least-privilege, or defense-in-depth for the problem at hand — call it out.

7. Be terse. Flag the risk, the impact, and the fix. Skip everything else.
""",

    "AI Engineer": """I am an AI Engineer specializing in machine learning and data science for the Elastic Suite application.
You are my AI system design advisor. Follow these rules:

1. Challenge assumptions about data requirements, model architecture, and training pipelines.
2. Rate confidence on technical claims with [Certain], [Likely], or [Guessing].
3. Avoid validation before interrogating design choices.
4. Focus on: data quality, model interpretability, computational efficiency, and deployment scalability.
5. Flag any potential overfitting, data bias, or inference latency issues.
6. Be concise. Provide technical alternatives when appropriate.
""",
}
# Global conversation state
conversation_history = []
context_window_usage = []
current_model = MODEL
current_role = DEFAULT_ROLE

def estimate_tokens(text):
    """Estimate token count for text (rough approximation)"""
    # Rough estimate: ~1 token per 4 characters
    return len(text) // 4


def clean_response(text):
    """Remove note portions and clean up extra whitespace from response"""
    # Remove lines containing "Note:" and everything after
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if 'Note:' in line.lower():
            break
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Remove excessive whitespace and newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()
    
    return text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/roles', methods=['GET'])
def get_roles():
    """Return available advisor roles"""
    return jsonify({
        'success': True,
        'roles': list(SYSTEM_PROMPTS.keys()),
        'current': current_role
    })

@app.route('/api/models', methods=['GET'])
def get_models():
    """Fetch available models from Ollama endpoint"""
    try:
        response = requests.get(
            f"{OLLAMA_BASE}/models",
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        models = [m['id'] for m in result.get('data', [])]
        return jsonify({'success': True, 'models': models, 'current': current_model})
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/start-conversation', methods=['POST'])
def start_conversation():
    """Start a new conversation with user's initial prompt"""
    global conversation_history, context_window_usage, current_model, current_role

    data = request.json
    initial_prompt = data.get('prompt', '')
    current_model = data.get('model', MODEL)
    current_role = data.get('role', DEFAULT_ROLE)

    # Reset state
    conversation_history = []
    context_window_usage = []

    # Add user message to history
    conversation_history.append({"role": "user", "content": initial_prompt})

    system_prompt = SYSTEM_PROMPTS.get(current_role, SYSTEM_PROMPTS[DEFAULT_ROLE])
    # Build messages
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    try:
        response = requests.post(
            OLLAMA_ENDPOINT,
            json={
                "model": current_model,
                "messages": messages,
                "stream": False
            },
            timeout=1500
        )
        response.raise_for_status()

        result = response.json()

        ai_response = clean_response(result['choices'][0]['message']['content'])
        conversation_history.append({"role": "assistant", "content": ai_response})

        # Track context window usage
        usage = result.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)

        context_window_usage.append({
            'prompt': prompt_tokens,
            'completion': completion_tokens,
            'total': total_tokens
        })

        context_used = sum(t['total'] for t in context_window_usage)
        context_remaining = MAX_CONTEXT - context_used

        return jsonify({
            'success': True,
            'response': ai_response,
            'conversation': conversation_history,
            'context_used': context_used,
            'context_remaining': context_remaining,
            'max_context': MAX_CONTEXT,
            'usage_percentage': (context_used / MAX_CONTEXT) * 100,
            'current_exchange': {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens
            },
            'total_exchanges': len(context_window_usage)
        })

    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/continue-conversation', methods=['POST'])
def continue_conversation():
    """Continue the conversation based on user input"""
    global conversation_history, context_window_usage

    data = request.json
    user_input = data.get('input', '')

    if not user_input:
        return jsonify({'success': False, 'error': 'No input provided'}), 400

    if not conversation_history:
        return jsonify({'success': False, 'error': 'No conversation started yet'}), 400

    # Check if we have enough context
    context_used = sum(t['total'] for t in context_window_usage)
    if context_used >= MAX_CONTEXT:
        return jsonify({
            'success': False,
            'error': 'Context window exhausted. Token limit reached.',
            'context_used': context_used,
            'max_context': MAX_CONTEXT
        }), 400

    # Append user message and send full history
    conversation_history.append({"role": "user", "content": user_input})
    system_prompt_cont = SYSTEM_PROMPTS.get(current_role, SYSTEM_PROMPTS[DEFAULT_ROLE])
    messages = [{"role": "system", "content": system_prompt_cont}] + conversation_history

    try:
        response = requests.post(
            OLLAMA_ENDPOINT,
            json={
                "model": current_model,
                "messages": messages,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()

        result = response.json()

        ai_response = clean_response(result['choices'][0]['message']['content'])
        conversation_history.append({"role": "assistant", "content": ai_response})

        # Track context usage
        usage = result.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)

        context_window_usage.append({
            'prompt': prompt_tokens,
            'completion': completion_tokens,
            'total': total_tokens
        })

        context_used = sum(t['total'] for t in context_window_usage)
        context_remaining = MAX_CONTEXT - context_used

        return jsonify({
            'success': True,
            'response': ai_response,
            'conversation': conversation_history,
            'context_used': context_used,
            'context_remaining': context_remaining,
            'max_context': MAX_CONTEXT,
            'usage_percentage': (context_used / MAX_CONTEXT) * 100,
            'current_exchange': {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens
            },
            'total_exchanges': len(context_window_usage),
            'compression_threshold': MAX_CONTEXT * 0.5
        })

    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get current conversation stats"""
    context_used = sum(t['total'] for t in context_window_usage)
    context_remaining = MAX_CONTEXT - context_used

    return jsonify({
        'context_used': context_used,
        'context_remaining': context_remaining,
        'max_context': MAX_CONTEXT,
        'usage_percentage': (context_used / MAX_CONTEXT) * 100,
        'exchanges': len(context_window_usage),
        'history': context_window_usage
    })

@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the conversation"""
    global conversation_history, context_window_usage, current_model, current_role
    conversation_history = []
    context_window_usage = []
    current_model = MODEL
    current_role = DEFAULT_ROLE
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)

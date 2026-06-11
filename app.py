from flask import Flask, render_template, request, jsonify
import requests
import json
import re

app = Flask(__name__)

# Configuration
OLLAMA_ENDPOINT = "http://192.168.86.141:11434/v1/chat/completions"
MODEL = "gemma4:12b-128k"
MAX_CONTEXT = 131130
SYSTEM_PROMPT = """I am the director of Application Development for a small B2B application called Elastic Suite.
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
"""
# Global conversation state
conversation_history = []
context_window_usage = []

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

@app.route('/api/start-conversation', methods=['POST'])
def start_conversation():
    """Start a new conversation with user's initial prompt"""
    global conversation_history, context_window_usage

    data = request.json
    initial_prompt = data.get('prompt', '')

    # Reset state
    conversation_history = []
    context_window_usage = []

    # Add user message to history
    conversation_history.append({"role": "user", "content": initial_prompt})

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    try:
        response = requests.post(
            OLLAMA_ENDPOINT,
            json={
                "model": MODEL,
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
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    try:
        response = requests.post(
            OLLAMA_ENDPOINT,
            json={
                "model": MODEL,
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
    global conversation_history, context_window_usage
    conversation_history = []
    context_window_usage = []
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)

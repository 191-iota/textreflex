import os
import json
import re
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# HuggingFace API configuration
HF_API_TOKEN = os.environ.get('HF_API_TOKEN', '')
HF_API_URL = "https://api-inference.huggingface.co/v1/chat/completions"
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

# The exact prompt from the original backend
ANALYSIS_PROMPT = """Analyze the following text for emotional-manipulation strategies:
- Identify each strategy (fear, urgency, scapegoating, polarization, tone).
- Rate each on scale <none/low/mid/high: why>.
- Provide the exact character or sentence ranges for each rating.
- Call out any false or misleading ("BS") claims with brief reasoning and ranges.
- List the top three most manipulative passages under "top_passages".
Be ultra-concise. Output ONLY valid JSON matching this schema exactly:

{
  "ratings": { /* strategy: "level: short label" */ },
  "passages": { /* strategy: "start–end" */ },
  "bs_callout": "yes/no",
  "bs_passage": "start–end",
  "top_passages": ["start–end", ...],
  "conclusion": "cold logic meta analysis about the ulterior manipulative motive OF THE TEXT what does the text as a whole try to achieve here? how does it try to change the perception of the reader? should be meta motive analysis not a rhethorical analysis"
}"""


@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze text for bias and manipulation using HuggingFace API"""
    try:
        # Get text from request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({'error': 'Empty text provided'}), 400
        
        if len(text) > 5000:
            return jsonify({'error': 'Text exceeds 5000 character limit'}), 400
        
        # Check for API token
        if not HF_API_TOKEN:
            return jsonify({'error': 'HuggingFace API token not configured. Please set the HF_API_TOKEN environment variable.'}), 500
        
        # Call HuggingFace API
        headers = {
            'Authorization': f'Bearer {HF_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": HF_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": f"{ANALYSIS_PROMPT}\n\nText to analyze:\n{text}"
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.text
            return jsonify({
                'error': f'AI API error: {response.status_code}',
                'details': error_msg
            }), 500
        
        # Parse AI response
        ai_response = response.json()
        
        if 'choices' not in ai_response or not ai_response['choices']:
            return jsonify({'error': 'Invalid AI response format'}), 500
        
        ai_content = ai_response['choices'][0]['message']['content']
        
        # Strip markdown code fences if present
        ai_content = re.sub(r'^```json\s*\n?', '', ai_content, flags=re.MULTILINE)
        ai_content = re.sub(r'\n?```\s*$', '', ai_content, flags=re.MULTILINE)
        ai_content = ai_content.strip()
        
        # Parse JSON response
        try:
            result = json.loads(ai_content)
        except json.JSONDecodeError as e:
            return jsonify({
                'error': 'Failed to parse AI response as JSON',
                'details': str(e),
                'raw_response': ai_content
            }), 500
        
        # Validate expected fields
        required_fields = ['ratings', 'passages', 'conclusion', 'bs_callout']
        for field in required_fields:
            if field not in result:
                result[field] = {} if field in ['ratings', 'passages'] else 'N/A'
        
        # Ensure optional fields exist
        if 'bs_passage' not in result:
            result['bs_passage'] = ''
        if 'top_passages' not in result:
            result['top_passages'] = []
        
        return jsonify(result)
    
    except requests.Timeout:
        return jsonify({'error': 'AI API request timed out'}), 504
    except requests.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


if __name__ == '__main__':
    # Only enable debug mode in development (check for DEBUG env var)
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

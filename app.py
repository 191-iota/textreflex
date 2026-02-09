import os
import json
import re
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Configuration constants
MAX_LOG_LENGTH = 500  # Maximum length for logging/error responses

# Pollinations AI API configuration (free, no auth required)
# Pollinations returns plain text responses, not OpenAI JSON format
AI_API_URL = "https://text.pollinations.ai/"

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
    """Analyze text for bias and manipulation using Pollinations AI"""
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
        
        # Build headers - no auth required for Pollinations AI
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Call Pollinations AI API (free, no auth required)
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You must output ONLY valid JSON. Do not include any markdown code fences or explanatory text, just the raw JSON object."
                },
                {
                    "role": "user",
                    "content": f"{ANALYSIS_PROMPT}\n\nText to analyze:\n{text}"
                }
            ],
            "model": "openai",
            "jsonMode": True,
            "seed": 42
        }
        
        # Increase timeout to 120 seconds for slow free API
        response = requests.post(AI_API_URL, headers=headers, json=payload, timeout=120)
        
        # Add debug logging
        app.logger.info(f"AI API status: {response.status_code}")
        app.logger.info(f"AI API response (first {MAX_LOG_LENGTH} chars): {response.text[:MAX_LOG_LENGTH]}")
        
        if response.status_code != 200:
            return jsonify({'error': f'AI API error: {response.status_code}', 'details': response.text}), 500
        
        # Pollinations returns plain text, not OpenAI JSON format
        ai_content = response.text.strip()
        
        # Strip markdown code fences if present
        ai_content = re.sub(r'^```(?:json)?\s*\n?', '', ai_content, flags=re.MULTILINE)
        ai_content = re.sub(r'\n?```\s*$', '', ai_content, flags=re.MULTILINE)
        ai_content = ai_content.strip()
        
        # Try to parse JSON directly first
        result = None
        try:
            result = json.loads(ai_content)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the response
            # Find the first { and last } to extract the JSON object
            json_start = ai_content.find('{')
            json_end = ai_content.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                try:
                    result = json.loads(ai_content[json_start:json_end + 1])
                except json.JSONDecodeError as e:
                    return jsonify({
                        'error': 'Failed to parse AI response as JSON',
                        'details': str(e),
                        'raw_response': ai_content[:MAX_LOG_LENGTH]
                    }), 500
            else:
                return jsonify({
                    'error': 'Failed to parse AI response as JSON',
                    'details': 'No valid JSON found in response',
                    'raw_response': ai_content[:MAX_LOG_LENGTH]
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
        return jsonify({'error': 'AI API request timed out. Please try again.'}), 504
    except requests.RequestException as e:
        return jsonify({'error': 'Unable to connect to AI service. Please check your internet connection and try again.'}), 500
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500


if __name__ == '__main__':
    # Only enable debug mode in development (check for DEBUG env var)
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

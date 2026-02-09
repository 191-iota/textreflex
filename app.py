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

# Valid Pollinations AI models (as of 2025)
# Ordered by preference: direct-output models first, then fallbacks
VALID_MODELS = ["mistral-large", "mistral", "llama", "command-r-plus", "openai"]

# The exact prompt from the original backend
ANALYSIS_PROMPT = """Analyze the following text for emotional-manipulation strategies:
- Identify each strategy (fear, urgency, scapegoating, polarization, tone).
- Rate each on scale <none/low/mid/high/very high: why>.
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
        # Try multiple models with fallback mechanism
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
            "model": "mistral-large",  # Will be updated in loop
            "jsonMode": True
        }
        
        # Try models in order until one succeeds (fallback for 404 errors)
        response = None
        last_error = None
        for model_name in VALID_MODELS:
            payload["model"] = model_name
            app.logger.info(f"Trying model: {model_name}")
            
            try:
                # Increase timeout to 120 seconds for slow free API
                response = requests.post(AI_API_URL, headers=headers, json=payload, timeout=120)
                
                # Add debug logging
                app.logger.info(f"AI API status for {model_name}: {response.status_code}")
                app.logger.info(f"AI API response (first {MAX_LOG_LENGTH} chars): {response.text[:MAX_LOG_LENGTH]}")
                
                # If we get a 404, try the next model
                if response.status_code == 404:
                    last_error = f"Model '{model_name}' not found (404)"
                    app.logger.warning(last_error)
                    continue
                
                # If we got a non-404 status, break and use this response
                break
                
            except requests.Timeout:
                last_error = f"Timeout with model '{model_name}'"
                app.logger.warning(last_error)
                continue
            except requests.RequestException as e:
                last_error = f"Request error with model '{model_name}': {str(e)}"
                app.logger.warning(last_error)
                continue
        
        # If all models failed, return error
        if response is None or response.status_code == 404:
            return jsonify({
                'error': 'All AI models failed',
                'details': last_error or 'Unable to connect to AI service'
            }), 500
        
        if response.status_code != 200:
            return jsonify({'error': f'AI API error: {response.status_code}', 'details': response.text}), 500
        
        # Pollinations returns plain text — get the raw response
        ai_content = response.text.strip()

        # Try to parse as JSON first (some models return JSON wrapper)
        result = None
        try:
            parsed_response = json.loads(ai_content)
            
            # Check if it's a chat completion style response
            if isinstance(parsed_response, dict):
                # Check for content in standard locations
                content = None
                
                # Try choices[0].message.content (OpenAI format)
                if 'choices' in parsed_response:
                    content = parsed_response['choices'][0].get('message', {}).get('content', '')
                
                # Try direct content field
                if not content and 'content' in parsed_response:
                    content = parsed_response['content']
                
                # FALLBACK: If content is empty but reasoning_content exists,
                # try to extract JSON from reasoning_content
                if not content and 'reasoning_content' in parsed_response:
                    reasoning = parsed_response['reasoning_content']
                    # Try to find a JSON object in the reasoning by finding balanced braces
                    # Start from the first { and find its matching }
                    start_idx = reasoning.find('{')
                    if start_idx != -1:
                        brace_count = 1  # We already have the opening brace
                        for i in range(start_idx + 1, len(reasoning)):
                            if reasoning[i] == '{':
                                brace_count += 1
                            elif reasoning[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    content = reasoning[start_idx:i+1]
                                    break
                
                if content:
                    ai_content = content
                # else: ai_content stays as the raw response text, we'll try to extract JSON below
                
                # If the parsed response itself has our expected fields, use it directly
                # (this avoids unnecessary re-parsing of ai_content)
                if all(k in parsed_response for k in ['ratings', 'passages', 'conclusion', 'bs_callout']):
                    result = parsed_response
                    
        except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as e:
            # Not JSON — treat as plain text (which is normal for Pollinations)
            app.logger.debug(f"Response parsing exception: {type(e).__name__}: {e}")
            pass
        
        # If we don't have a result yet, try to parse ai_content
        if result is None:
            # Strip markdown code fences if present
            ai_content = re.sub(r'^```(?:json)?\s*\n?', '', ai_content, flags=re.MULTILINE)
            ai_content = re.sub(r'\n?```\s*$', '', ai_content, flags=re.MULTILINE)
            ai_content = ai_content.strip()
            
            # Try to parse JSON directly first
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

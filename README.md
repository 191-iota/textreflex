# Textreflex AI

A lightweight Flask application for detecting emotional manipulation and bias in text using AI.

## Features

- 🧠 AI-powered bias and manipulation detection
- 🎨 Clean, dark-themed UI with glassmorphic design
- 📊 Color-coded severity ratings for manipulation strategies
- 🚀 Minimal dependencies (Flask + HuggingFace API)
- 📱 Responsive design for mobile and desktop

## What It Does

Textreflex analyzes text to identify:
- **Manipulation strategies**: fear, urgency, scapegoating, polarization, tone
- **Severity levels**: none, low, mid, high, very high
- **Misleading claims**: BS detection with reasoning
- **Top manipulative passages**: most concerning sections
- **Meta analysis**: overall manipulative intent of the text

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- A HuggingFace account and API token (free tier available)

### 1. Clone the Repository

```bash
git clone https://github.com/191-iota/textreflex.git
cd textreflex
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your HuggingFace API token:

```
HF_API_TOKEN=your_actual_token_here
# Optional: Set FLASK_DEBUG=true for development (never in production!)
```

To get a free HuggingFace API token:
1. Sign up at https://huggingface.co
2. Go to https://huggingface.co/settings/tokens
3. Create a new token with "Read" access
4. Copy and paste it into your `.env` file

**Security Note:** Never set `FLASK_DEBUG=true` in production as it can expose sensitive information and allow arbitrary code execution.

### 5. Run the Application

```bash
flask run
```

Or:

```bash
python app.py
```

The app will be available at http://localhost:5000

## Usage

1. Open http://localhost:5000 in your browser
2. Paste any text (up to 5000 characters) into the textarea
3. Check the disclaimer checkbox
4. Click "Analyze Text"
5. Wait for the AI analysis (usually 10-30 seconds)
6. Review the results:
   - **Meta Analysis**: Overall manipulative intent
   - **Manipulation Strategies**: Color-coded severity ratings
   - **BS Detection**: Flagged misleading claims
   - **Top Passages**: Most manipulative sections

## Color Coding

- 🟢 **Green** (None): No manipulation detected
- 🔵 **Light Blue** (Low): Minimal manipulation
- 🔵 **Blue** (Mid): Moderate manipulation
- 🟡 **Yellow** (High): Significant manipulation
- 🔴 **Red** (Very High): Severe manipulation

## Technical Stack

- **Backend**: Python Flask
- **Frontend**: Vanilla HTML/CSS/JavaScript (no frameworks)
- **AI Provider**: HuggingFace Inference API (free tier)
- **Model**: Mistral-7B-Instruct-v0.3
- **Database**: None (stateless application)

## Project Structure

```
textreflex/
├── app.py                 # Flask backend with API endpoints
├── templates/
│   └── index.html        # Single-page frontend
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Development

The application is intentionally minimal with no build steps, no database, and no heavy frameworks. To make changes:

1. Edit `app.py` for backend logic
2. Edit `templates/index.html` for frontend UI
3. Restart Flask to see changes (or use `flask run --reload`)

## Limitations

- Free HuggingFace API has rate limits and may be slower than premium tiers
- Analysis quality depends on the AI model's capabilities
- Results are for educational purposes and should not be considered definitive
- Maximum text length: 5000 characters

## License

MIT

## Credits

Built as a lightweight replacement for the original two-repository TextReflex stack (Angular + Spring Boot).
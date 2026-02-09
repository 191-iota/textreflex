# Textreflex AI

A lightweight Flask application for detecting emotional manipulation and bias in text using AI.

## Features

- 🧠 AI-powered bias and manipulation detection
- 🎨 Clean, dark-themed UI with glassmorphic design
- 📊 Color-coded severity ratings for manipulation strategies
- 🚀 **Works out of the box** - no API keys, no sign-ups, zero configuration required
- 📱 Responsive design for mobile and desktop
- ⚡ Uses free Pollinations AI - completely free, no rate limits

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
- **That's it!** No API keys, no accounts, no configuration needed

### Quick Start (3 steps)

```bash
# 1. Clone the repository
git clone https://github.com/191-iota/textreflex.git
cd textreflex

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
flask run
```

The app will be available at http://localhost:5000

**That's literally it!** Just clone, install, and run. Zero configuration required.

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
- **AI Provider**: Pollinations AI (completely free, no auth required)
- **Model**: OpenAI-compatible models via Pollinations
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

- Analysis quality depends on the AI model's capabilities
- Results are for educational purposes and should not be considered definitive
- Maximum text length: 5000 characters
- Response time may vary based on API availability (usually 10-30 seconds)

## License

MIT

## Credits

Built as a lightweight replacement for the original two-repository TextReflex stack (Angular + Spring Boot).
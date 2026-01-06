# User Guide

## Setup
1. Install Python 3.10+ and create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and populate required keys.

## CLI (entry point)
- Run `python -m src.content_generator` for a quick smoke test.

## GUI
1. Set `FLASK_APP=gui.app:app`.
2. Run `flask run --debug`.
3. Open the printed URL and submit a topic.

## Tests
- Execute `pytest --cov=src`.

## Troubleshooting
- Ensure `OPENAI_API_KEY` is set and valid.
- Check network access to the OpenAI API.
- Run `flake8` and `black` before committing code changes.

# Deployment Guide

## Quick Deploy Options

### Option 1: Railway.app (Recommended)
1. Create account at railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select this repository
4. Add environment variables:
   - `OPENAI_API_KEY=your_key_here`
   - `FLASK_ENV=production`
5. Deploy!

### Option 2: Render
1. Create account at render.com
2. New → Web Service
3. Connect GitHub repository
4. Build command: `pip install -r requirements.txt`
5. Start command: `python gui/app.py`

### Option 3: Heroku
See detailed guide in `docs/heroku-deploy.md`

## Environment Variables Required
- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - Flask secret key (generate with `python -c "import secrets; print(secrets.token_hex(16))"`)
- `FLASK_ENV` - Set to `production`

## Post-Deployment
- Test all endpoints: `/api/templates`, `/api/generate`
- Set rate limits appropriately
- Monitor usage and costs

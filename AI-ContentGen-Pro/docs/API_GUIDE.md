# API Guide

## Environment
- Configure `.env` with `OPENAI_API_KEY`, `OPENAI_MODEL`, `MAX_TOKENS`, `TEMPERATURE`.

## Core Classes
- `APIManager.chat_completion(messages, **overrides)`: submit chat messages and return string content.
- `PromptEngine.register(name, template)`: add or update templates.
- `PromptEngine.render(name, context)`: render a template.
- `ContentGenerator.generate(template_name, context)`: render and call the API.

## Sample Usage
```python
from src.content_generator import ContentGenerator
from src.prompt_engine import PromptEngine

engine = PromptEngine()
engine.register("blog", "Write a concise blog intro about ${topic}.")

cg = ContentGenerator(prompt_engine=engine)
print(cg.generate("blog", {"topic": "AI safety"}))
```

## HTTP Endpoints (Flask GUI)
- `GET /`: returns the HTML UI.
- `POST /generate`: JSON body `{ "template": "default", "context": {"topic": "..."} }`.

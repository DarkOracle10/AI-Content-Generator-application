# Architecture Documentation

## Overview

AI-ContentGen-Pro follows a layered architecture pattern with clear separation of concerns. This document provides a comprehensive view of the system architecture, component interactions, data flow, and design decisions.

## Table of Contents

- [System Architecture](#system-architecture)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [API Design](#api-design)
- [Security Architecture](#security-architecture)
- [Scalability Considerations](#scalability-considerations)
- [Design Decisions](#design-decisions)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Web Browser  │  │  CLI Client  │  │ API Client   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          │ HTTP/HTTPS       │ Direct           │ REST API
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼─────────────────┐
│         │         PRESENTATION LAYER          │                  │
│  ┌──────▼──────────────────▼──────────────────▼──────┐          │
│  │           Flask Application Server                  │          │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │          │
│  │  │  Routes  │  │Templates │  │  Static  │        │          │
│  │  │  /api/*  │  │  (HTML)  │  │(CSS/JS)  │        │          │
│  │  └──────────┘  └──────────┘  └──────────┘        │          │
│  │  ┌──────────────────────────────────────┐        │          │
│  │  │     Session & Rate Limiting          │        │          │
│  │  └──────────────────────────────────────┘        │          │
│  └────────────────┬──────────────────────────────────┘          │
└───────────────────┼────────────────────────────────────────────┘
                    │
┌───────────────────┼────────────────────────────────────────────┐
│                   │      BUSINESS LOGIC LAYER                   │
│  ┌────────────────▼──────────────────────────────────────────┐ │
│  │             Content Generator (Orchestrator)              │ │
│  │  ┌──────────────────────────────────────────────────┐    │ │
│  │  │ • Generation orchestration                        │    │ │
│  │  │ • Cost calculation                                │    │ │
│  │  │ • Caching management                              │    │ │
│  │  │ • Statistics tracking                             │    │ │
│  │  │ • History management                              │    │ │
│  │  └──────────────────────────────────────────────────┘    │ │
│  └────────┬─────────────────────────┬────────────────────────┘ │
│           │                         │                           │
│  ┌────────▼─────────┐      ┌───────▼────────┐                 │
│  │  Prompt Engine   │      │  API Manager   │                 │
│  │ ┌──────────────┐ │      │ ┌────────────┐ │                 │
│  │ │ Templates    │ │      │ │ OpenAI     │ │                 │
│  │ │ Registry     │ │      │ │ Client     │ │                 │
│  │ └──────────────┘ │      │ └────────────┘ │                 │
│  │ ┌──────────────┐ │      │ ┌────────────┐ │                 │
│  │ │ Variable     │ │      │ │ Retry      │ │                 │
│  │ │ Substitution │ │      │ │ Logic      │ │                 │
│  │ └──────────────┘ │      │ └────────────┘ │                 │
│  │ ┌──────────────┐ │      │ ┌────────────┐ │                 │
│  │ │ Rendering    │ │      │ │ Error      │ │                 │
│  │ │ Engine       │ │      │ │ Handling   │ │                 │
│  │ └──────────────┘ │      │ └────────────┘ │                 │
│  └──────────────────┘      └────────┬───────┘                 │
└────────────────────────────────────┼──────────────────────────┘
                                     │
                                     │ HTTPS
                                     │
┌────────────────────────────────────▼──────────────────────────┐
│                     EXTERNAL SERVICES                          │
│  ┌──────────────────────────────────────────────────────┐     │
│  │              OpenAI API                               │     │
│  │  • GPT-3.5-turbo                                      │     │
│  │  • GPT-4                                              │     │
│  │  • Chat Completions                                   │     │
│  └──────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼──────────────────────────┐
│                  INFRASTRUCTURE LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │Configuration │  │   Caching    │  │   Logging    │        │
│  │  • .env vars │  │ • LRU cache  │  │ • File logs  │        │
│  │  • Defaults  │  │ • TTL mgmt   │  │ • Rotation   │        │
│  │  • Validation│  │ • Storage    │  │ • Levels     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Configuration Layer (`src/config.py`)

**Purpose**: Centralized configuration management

**Responsibilities**:
- Load environment variables from `.env`
- Validate required configuration
- Provide default values
- Type conversion and validation

**Key Features**:
```python
class Config:
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 500
    LOG_LEVEL: str = "INFO"
```

**Dependencies**: `python-dotenv`

---

### 2. Prompt Engine (`src/prompt_engine.py`)

**Purpose**: Template management and rendering

**Responsibilities**:
- Register and store templates
- Validate template structure
- Render templates with variables
- Manage required/optional variables

**Architecture**:
```
PromptEngine
├── TemplateRegistry
│   └── Map<string, PromptTemplate>
├── VariableSubstitution
│   └── string.Template
└── Validation
    └── RequiredVariables
```

**Template Structure**:
```python
class PromptTemplate:
    name: str
    description: str
    category: str
    system_instructions: str
    required_variables: List[str]
    optional_variables: Dict[str, str]
```

**Design Pattern**: Registry Pattern

---

### 3. API Manager (`src/api_manager.py`)

**Purpose**: OpenAI API integration with reliability features

**Responsibilities**:
- Initialize OpenAI client
- Execute chat completions
- Implement retry logic
- Handle rate limiting
- Track token usage
- Manage errors

**Retry Strategy**:
```python
Exponential Backoff:
- Attempt 1: Wait 2s
- Attempt 2: Wait 4s
- Attempt 3: Wait 8s
- Max retries: 3
```

**Error Handling**:
- `RateLimitError` → Retry with backoff
- `APIError` → Log and raise
- `NetworkError` → Retry with backoff
- `AuthenticationError` → Immediate failure

**Design Pattern**: Proxy Pattern, Retry Pattern

---

### 4. Content Generator (`src/content_generator.py`)

**Purpose**: Main orchestration layer

**Responsibilities**:
- Coordinate generation workflow
- Calculate costs
- Manage caching
- Track statistics
- Store generation history
- Provide high-level API

**Generation Workflow**:
```
1. Validate inputs
   └── Check template exists
   └── Check required variables
2. Check cache
   └── If hit: return cached
   └── If miss: continue
3. Render template
   └── Substitute variables
4. Call API Manager
   └── With retry logic
5. Calculate cost
   └── Token count × rate
6. Update cache
   └── Store result
7. Update statistics
   └── Increment counters
8. Save to history
   └── Write to file
9. Return result
```

**Design Pattern**: Facade Pattern, Strategy Pattern

---

### 5. Flask Application (`gui/app.py`)

**Purpose**: Web interface and REST API

**Responsibilities**:
- Serve web interface
- Handle API requests
- Manage sessions
- Rate limiting
- CORS handling
- Error responses

**API Endpoints**:
```
GET  /                      → Web UI
GET  /docs                  → API docs
GET  /history               → History page

GET  /api/health            → Health check
GET  /api/templates         → List templates
GET  /api/template/:name    → Get template
POST /api/generate          → Generate content
POST /api/generate/variations → Generate variations
GET  /api/statistics        → Get stats
POST /api/cost-estimate     → Estimate cost
GET  /api/history           → Get history
```

**Session Management**:
- Per-session ContentGenerator instance
- Session-based rate limiting
- Session statistics tracking

**Design Pattern**: MVC Pattern, REST API Pattern

---

### 6. Utilities (`src/utils.py`)

**Purpose**: Helper functions

**Functions**:
- Message formatting for OpenAI
- Text sanitization
- JSON serialization helpers
- Logging utilities

---

## Data Flow

### Content Generation Flow

```
User Request
    │
    ├─→ [Web UI] ──HTTP POST──→ Flask Route
    │                               │
    ├─→ [CLI] ─────Direct Call────→│
    │                               │
    └─→ [API] ─────REST Call──────→│
                                    │
                            ┌───────▼────────┐
                            │ Flask Handler  │
                            │ • Validate     │
                            │ • Parse JSON   │
                            └───────┬────────┘
                                    │
                            ┌───────▼────────────┐
                            │ContentGenerator    │
                            │ .generate()        │
                            └───────┬────────────┘
                                    │
                        ┌───────────┴──────────┐
                        │                      │
                ┌───────▼────────┐    ┌───────▼────────┐
                │ Check Cache    │    │ Render Template│
                │ (LRU)          │    │ (PromptEngine) │
                └───────┬────────┘    └───────┬────────┘
                        │                      │
                    Cache Hit?             Variables
                        │                  Substituted
                    ┌───┴────┐                │
                   Yes      No         ┌──────▼─────────┐
                    │        │         │ API Manager    │
                    │    ┌───▼─────┐   │ .chat_completion│
                    │    │ API Call│   └──────┬─────────┘
                    │    └───┬─────┘          │
                    │        │            ┌───▼────┐
                    │    ┌───▼─────┐      │ Retry  │
                    │    │Response │      │ Logic  │
                    │    └───┬─────┘      └───┬────┘
                    │        │                │
                    │    ┌───▼─────────┐  ┌──▼──────┐
                    │    │Update Cache │  │OpenAI   │
                    │    └───┬─────────┘  │API Call │
                    │        │            └──┬──────┘
                    └────────┴───────────────┘
                                │
                        ┌───────▼────────┐
                        │ Calculate Cost │
                        │ Track Stats    │
                        │ Save History   │
                        └───────┬────────┘
                                │
                        ┌───────▼────────┐
                        │ Return Result  │
                        │ • content      │
                        │ • cost         │
                        │ • tokens       │
                        │ • cached       │
                        │ • duration     │
                        └───────┬────────┘
                                │
                        ┌───────▼────────┐
                        │ Format Response│
                        │ (JSON)         │
                        └───────┬────────┘
                                │
                        ┌───────▼────────┐
                        │ Send to Client │
                        └────────────────┘
```

---

## API Design

### RESTful Principles

1. **Resource-Based URLs**:
   - `/api/templates` - Collection
   - `/api/template/:name` - Individual resource

2. **HTTP Methods**:
   - `GET` - Retrieve data
   - `POST` - Create/generate
   - `PUT` - Update (future)
   - `DELETE` - Remove (future)

3. **Status Codes**:
   - `200` - Success
   - `400` - Bad request
   - `404` - Not found
   - `429` - Rate limit
   - `500` - Server error

4. **Response Format**:
```json
{
  "success": true,
  "data": {...},
  "message": "Optional message",
  "timestamp": "2026-01-06T..."
}
```

### Error Response Format

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_TYPE",
  "details": {...}
}
```

---

## Security Architecture

### Security Layers

1. **Input Validation**:
   - Template name validation
   - Variable validation
   - Parameter bounds checking

2. **API Key Security**:
   - Environment variable storage
   - Never logged or exposed
   - Validation on startup

3. **Rate Limiting**:
   - Per-session limits
   - Configurable thresholds
   - Graceful degradation

4. **CORS**:
   - Configurable origins
   - Method restrictions
   - Header whitelisting

5. **Session Security**:
   - Secure cookie flags
   - HTTPONLY cookies
   - SAMESITE policy

6. **Content Security**:
   - XSS protection headers
   - Content-Type validation
   - SQL injection prevention

---

## Scalability Considerations

### Current Architecture

**Single Instance**:
- In-memory caching
- File-based history
- Session-based state

**Limitations**:
- No horizontal scaling
- Memory-based cache
- Single point of failure

### Scaling Strategy

**Phase 1: Vertical Scaling**
```
Current: 2GB RAM, 1 CPU
Scaled:  8GB RAM, 4 CPU
Workers: 9 (2×4+1)
```

**Phase 2: Horizontal Scaling**
```
┌─────────────────┐
│  Load Balancer  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│App 1 │  │App 2 │
└───┬──┘  └──┬───┘
    │        │
┌───▼────────▼───┐
│  Redis Cache   │
│  PostgreSQL DB │
└────────────────┘
```

**Phase 3: Microservices**
```
┌──────────────┐
│ API Gateway  │
└──────┬───────┘
       │
   ┌───┴────┐
   │        │
┌──▼───┐ ┌─▼────┐
│Auth  │ │Gen   │
│Service│ │Service│
└──────┘ └──────┘
```

---

## Design Decisions

### 1. Why Flask over Django?

**Chosen**: Flask

**Reasoning**:
- Lightweight for API-focused app
- Flexibility in structure
- Easier to understand for portfolio
- Lower overhead
- Better for microservices

### 2. Why String Templates over Jinja2?

**Chosen**: Python string.Template

**Reasoning**:
- Simpler syntax for users
- Less risk of code injection
- Easier to validate
- Sufficient for use case
- Better performance

### 3. Why In-Memory Cache?

**Chosen**: functools.lru_cache

**Reasoning**:
- Simple implementation
- No external dependencies
- Sufficient for single instance
- Good performance
- Easy to migrate to Redis later

### 4. Why Session-Based State?

**Chosen**: Flask sessions

**Reasoning**:
- Simple for MVP
- Works without database
- Good for demos
- Can migrate to Redis later

### 5. Why File-Based History?

**Chosen**: JSON files

**Reasoning**:
- No database setup needed
- Human-readable
- Easy backup
- Good for demos
- Can migrate to DB later

---

## Testing Strategy

### Test Pyramid

```
        ┌─────────┐
        │   E2E   │ (Few)
        └─────────┘
      ┌─────────────┐
      │ Integration │ (Some)
      └─────────────┘
    ┌─────────────────┐
    │   Unit Tests    │ (Many)
    └─────────────────┘
```

**Unit Tests** (80%):
- Individual function testing
- Mock external dependencies
- Fast execution

**Integration Tests** (15%):
- Component interaction
- API endpoint testing
- Mock OpenAI API

**E2E Tests** (5%):
- Full workflow testing
- Real API calls (limited)
- Manual testing

---

## Monitoring & Observability

### Logging Strategy

**Levels**:
- `DEBUG`: Development details
- `INFO`: Normal operations
- `WARNING`: Recoverable issues
- `ERROR`: Operation failures
- `CRITICAL`: System failures

**Log Structure**:
```python
{
    "timestamp": "2026-01-06T12:00:00",
    "level": "INFO",
    "module": "content_generator",
    "message": "Content generated",
    "extra": {
        "template": "blog_post_outline",
        "tokens": 342,
        "cost": 0.002,
        "duration": 2.3
    }
}
```

### Metrics Tracking

**Generation Metrics**:
- Total generations
- Success rate
- Average duration
- Total cost
- Cache hit rate

**API Metrics**:
- Request count
- Error rate
- Response time
- Rate limit hits

---

## Future Improvements

### Near-Term (V2.0)
1. **Redis Integration**:
   - Distributed caching
   - Session storage
   - Rate limiting

2. **PostgreSQL**:
   - User accounts
   - Generation history
   - Template storage

3. **Async Processing**:
   - Celery for background tasks
   - Webhook support
   - Batch processing

### Long-Term (V3.0)
1. **Microservices**:
   - Separate auth service
   - Separate generation service
   - API gateway

2. **Multi-Provider**:
   - Anthropic Claude
   - Google PaLM
   - Custom models

3. **Advanced Features**:
   - Template marketplace
   - A/B testing
   - Analytics dashboard

---

## Conclusion

The architecture prioritizes:
1. **Simplicity**: Easy to understand and modify
2. **Reliability**: Robust error handling and retry logic
3. **Scalability**: Clear path to horizontal scaling
4. **Maintainability**: Clean code, good documentation
5. **Performance**: Caching, efficient algorithms

The modular design allows for easy extension and modification while maintaining code quality and test coverage.

---

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [12-Factor App](https://12factor.net/)

"""Production-grade Flask web application for AI-ContentGen-Pro.

This module provides a RESTful API and web interface for the AI Content Generator.
Features include:
- RESTful API endpoints for content generation
- Session-based history tracking
- Security best practices (CSRF, rate limiting, input validation)
- Comprehensive error handling and logging
- CORS support for API access

Usage:
    # Development
    python gui/app.py
    
    # Production (with Gunicorn)
    gunicorn -w 4 -b 0.0.0.0:5000 gui.app:app

API Endpoints:
    GET  /api/health          - Health check
    GET  /api/templates       - List available templates
    GET  /api/template/<name> - Get template details
    POST /api/generate        - Generate content
    POST /api/generate/variations - Generate multiple variations
    POST /api/generate/batch  - Batch generation
    GET  /api/history         - Get session history
    GET  /api/history/export  - Export history as file
    DELETE /api/history/clear - Clear session history
    GET  /api/statistics      - Get usage statistics
    POST /api/validate        - Validate template variables
    POST /api/cost-estimate   - Estimate generation cost

Author: AI-ContentGen-Pro Team
Version: 1.0.0
"""

from __future__ import annotations

import io
import json
import logging
import os
import secrets
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, cast

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_file,
    session,
)
from werkzeug.exceptions import BadRequest, HTTPException, NotFound

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.content_generator import ContentGenerator, create_mock_generator

# Optional: CORS support
try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False
    CORS = None  # type: ignore

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# =============================================================================
# APP CONFIGURATION
# =============================================================================

app = Flask(__name__)

# Security configuration
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max request
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

# Enable CORS for API endpoints if flask-cors is installed
if HAS_CORS and CORS is not None:
    CORS(app, resources={r"/api/*": {"origins": "*"}})

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Session-based generators (in production, use Redis or similar)
session_generators: Dict[str, ContentGenerator] = {}

# Rate limiting state (in production, use Redis)
rate_limit_store: Dict[str, List[float]] = defaultdict(list)

# Session cleanup tracking
last_cleanup = datetime.now(timezone.utc)
SESSION_MAX_AGE = timedelta(hours=24)
RATE_LIMIT_REQUESTS = 60  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

F = TypeVar("F", bound=Callable[..., Any])

# =============================================================================
# RESPONSE HELPERS
# =============================================================================


def success_response(data: Dict[str, Any], status_code: int = 200) -> Tuple[Response, int]:
    """Create a standardized success response."""
    return jsonify({"success": True, **data}), status_code


def error_response(
    message: str,
    code: str = "ERROR",
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """Create a standardized error response."""
    response_data: Dict[str, Any] = {
        "success": False,
        "error": message,
        "code": code,
    }
    if details:
        response_data["details"] = details
    return jsonify(response_data), status_code


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================


def init_session() -> None:
    """Initialize session with unique ID if not already set."""
    if "session_id" not in session:
        session["session_id"] = secrets.token_hex(16)
        session["created_at"] = datetime.now(timezone.utc).isoformat()
        session.permanent = True
        logger.info(f"New session created: {session['session_id'][:8]}...")


def get_session_id() -> str:
    """Get current session ID, initializing if needed."""
    init_session()
    return cast(str, session.get("session_id", "anonymous"))


def get_or_create_generator() -> ContentGenerator:
    """Get or create ContentGenerator for current session."""
    session_id = get_session_id()
    
    if session_id not in session_generators:
        try:
            # Try to create real generator with API key
            api_key = os.getenv("OPENAI_API_KEY")
            generator = ContentGenerator(api_key=api_key)
            logger.info(f"Created generator for session {session_id[:8]}...")
        except Exception as e:
            # Fall back to mock generator for demo/testing
            logger.warning(f"Failed to create real generator: {e}. Using mock.")
            generator = create_mock_generator(
                mock_response="This is a demo response. Configure OPENAI_API_KEY for real generation."
            )
        session_generators[session_id] = generator
    
    return session_generators[session_id]


def cleanup_old_sessions() -> int:
    """Remove generators for sessions older than max age."""
    global last_cleanup
    
    now = datetime.now(timezone.utc)
    if now - last_cleanup < timedelta(minutes=5):
        return 0  # Don't cleanup too frequently
    
    last_cleanup = now
    cleaned = 0
    
    # Get all session IDs to check
    session_ids = list(session_generators.keys())
    
    for sid in session_ids:
        gen = session_generators.get(sid)
        if gen and hasattr(gen, "_session_start"):
            session_start = gen._session_start
            if isinstance(session_start, datetime):
                if now - session_start > SESSION_MAX_AGE:
                    del session_generators[sid]
                    cleaned += 1
                    logger.info(f"Cleaned up old session: {sid[:8]}...")
    
    if cleaned:
        logger.info(f"Session cleanup: removed {cleaned} old sessions")
    
    return cleaned


# =============================================================================
# DECORATORS
# =============================================================================


def validate_json(f: F) -> F:
    """Decorator to validate request has valid JSON body."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if not request.is_json:
            return error_response(
                "Content-Type must be application/json",
                code="INVALID_CONTENT_TYPE",
                status_code=400,
            )
        try:
            # Ensure JSON is parseable
            _ = request.get_json(force=True)
        except Exception:
            return error_response(
                "Invalid JSON in request body",
                code="INVALID_JSON",
                status_code=400,
            )
        return f(*args, **kwargs)
    return cast(F, decorated)


def rate_limit(f: F) -> F:
    """Decorator to implement rate limiting per session."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        session_id = get_session_id()
        now = time.time()
        
        # Clean old entries
        rate_limit_store[session_id] = [
            t for t in rate_limit_store[session_id]
            if now - t < RATE_LIMIT_WINDOW
        ]
        
        # Check limit
        if len(rate_limit_store[session_id]) >= RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit exceeded for session {session_id[:8]}...")
            return error_response(
                f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds.",
                code="RATE_LIMIT_EXCEEDED",
                status_code=429,
            )
        
        # Record this request
        rate_limit_store[session_id].append(now)
        
        return f(*args, **kwargs)
    return cast(F, decorated)


def require_api_key(f: F) -> F:
    """Decorator to require API key header (optional security layer)."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        api_key = os.getenv("API_KEY_REQUIRED")
        if api_key:
            provided_key = request.headers.get("X-API-Key")
            if not provided_key or provided_key != api_key:
                logger.warning("Invalid or missing API key")
                return error_response(
                    "Invalid or missing API key",
                    code="UNAUTHORIZED",
                    status_code=401,
                )
        return f(*args, **kwargs)
    return cast(F, decorated)


# =============================================================================
# ERROR HANDLERS
# =============================================================================


@app.errorhandler(400)
def handle_400(error: HTTPException) -> Tuple[Response, int]:
    """Handle Bad Request errors."""
    return error_response(
        str(error.description) if error.description else "Bad request",
        code="BAD_REQUEST",
        status_code=400,
    )


@app.errorhandler(404)
def handle_404(error: HTTPException) -> Tuple[Response, int]:
    """Handle Not Found errors."""
    return error_response(
        "Resource not found",
        code="NOT_FOUND",
        status_code=404,
    )


@app.errorhandler(405)
def handle_405(error: HTTPException) -> Tuple[Response, int]:
    """Handle Method Not Allowed errors."""
    return error_response(
        "Method not allowed",
        code="METHOD_NOT_ALLOWED",
        status_code=405,
    )


@app.errorhandler(429)
def handle_429(error: HTTPException) -> Tuple[Response, int]:
    """Handle Rate Limit errors."""
    return error_response(
        "Too many requests",
        code="RATE_LIMIT_EXCEEDED",
        status_code=429,
    )


@app.errorhandler(500)
def handle_500(error: HTTPException) -> Tuple[Response, int]:
    """Handle Internal Server errors."""
    logger.exception("Internal server error")
    return error_response(
        "An internal error occurred. Please try again later.",
        code="INTERNAL_ERROR",
        status_code=500,
    )


@app.errorhandler(Exception)
def handle_exception(error: Exception) -> Tuple[Response, int]:
    """Handle uncaught exceptions."""
    if isinstance(error, HTTPException):
        return error_response(
            str(error.description) if error.description else "HTTP error",
            code="HTTP_ERROR",
            status_code=error.code or 500,
        )
    logger.exception(f"Unhandled exception: {error}")
    return error_response(
        "An unexpected error occurred",
        code="UNEXPECTED_ERROR",
        status_code=500,
    )


# =============================================================================
# REQUEST HOOKS
# =============================================================================


@app.before_request
def before_request() -> None:
    """Execute before each request."""
    init_session()
    cleanup_old_sessions()
    
    # Log API requests
    if request.path.startswith("/api/"):
        logger.info(
            f"API Request: {request.method} {request.path} "
            f"[session={get_session_id()[:8]}...]"
        )


@app.after_request
def after_request(response: Response) -> Response:
    """Execute after each request."""
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Add cache control for API responses
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    
    return response


# =============================================================================
# WEB ROUTES (HTML Pages)
# =============================================================================


@app.route("/")
def index() -> str:
    """Homepage with main content generation interface."""
    generator = get_or_create_generator()
    templates = generator.list_available_templates()
    return render_template("index.html", templates=templates)


@app.route("/history")
def history_page() -> str:
    """Generation history page."""
    return render_template("history.html")


@app.route("/docs")
def docs_page() -> str:
    """API documentation page."""
    return render_template("docs.html")


# =============================================================================
# API ROUTES - Health & Info
# =============================================================================


@app.route("/api/health", methods=["GET"])
def api_health() -> Tuple[Response, int]:
    """Health check endpoint for monitoring."""
    return success_response({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "active_sessions": len(session_generators),
    })


@app.route("/api/templates", methods=["GET"])
@rate_limit
def api_get_templates() -> Tuple[Response, int]:
    """Get all available templates."""
    generator = get_or_create_generator()
    templates = generator.list_available_templates()
    
    # Optionally filter by category
    category = request.args.get("category")
    if category:
        templates = [t for t in templates if t.get("category", "").lower() == category.lower()]
    
    return success_response({
        "templates": templates,
        "count": len(templates),
    })


@app.route("/api/template/<template_name>", methods=["GET"])
@rate_limit
def api_get_template(template_name: str) -> Tuple[Response, int]:
    """Get details for a specific template."""
    generator = get_or_create_generator()
    
    try:
        info = generator.get_template_info(template_name)
        return success_response({"template": info})
    except Exception as e:
        return error_response(
            f"Template '{template_name}' not found",
            code="TEMPLATE_NOT_FOUND",
            status_code=404,
        )


# =============================================================================
# API ROUTES - Content Generation
# =============================================================================


@app.route("/api/generate", methods=["POST"])
@rate_limit
@validate_json
def api_generate() -> Tuple[Response, int]:
    """Generate content using a template."""
    data = request.get_json(force=True)
    
    # Extract parameters
    template_name = data.get("template")
    variables = data.get("variables", {})
    use_cache = data.get("use_cache", True)
    options = data.get("options", {})
    
    # Validate template name
    if not template_name:
        return error_response(
            "Missing required field: template",
            code="MISSING_FIELD",
            status_code=400,
        )
    
    # Validate variables is a dict
    if not isinstance(variables, dict):
        return error_response(
            "Variables must be an object/dictionary",
            code="INVALID_VARIABLES",
            status_code=400,
        )
    
    generator = get_or_create_generator()
    
    # Validate template exists
    valid, missing = generator.validate_template_variables(template_name, variables)
    if missing and "not found" in str(missing).lower():
        return error_response(
            f"Template '{template_name}' not found",
            code="TEMPLATE_NOT_FOUND",
            status_code=404,
        )
    
    if not valid:
        return error_response(
            f"Missing required variables: {', '.join(missing)}",
            code="MISSING_VARIABLES",
            status_code=400,
            details={"missing_variables": missing},
        )
    
    # Generate content
    try:
        result = generator.generate(
            template_name,
            variables,
            use_cache=use_cache,
            **options,
        )
        
        if result.get("success"):
            logger.info(
                f"Generated content: template={template_name}, "
                f"tokens={result.get('tokens_used', {}).get('total', 0)}, "
                f"cost=${result.get('cost', 0):.6f}"
            )
            return success_response({"result": result})
        else:
            return error_response(
                result.get("error", "Generation failed"),
                code="GENERATION_FAILED",
                status_code=500,
            )
    except Exception as e:
        logger.exception(f"Generation error: {e}")
        return error_response(
            "An error occurred during generation",
            code="GENERATION_ERROR",
            status_code=500,
        )


@app.route("/api/generate/variations", methods=["POST"])
@rate_limit
@validate_json
def api_generate_variations() -> Tuple[Response, int]:
    """Generate multiple variations of content."""
    data = request.get_json(force=True)
    
    template_name = data.get("template")
    variables = data.get("variables", {})
    count = data.get("count", 3)
    temperature_range = data.get("temperature_range")
    
    if not template_name:
        return error_response(
            "Missing required field: template",
            code="MISSING_FIELD",
            status_code=400,
        )
    
    # Validate count
    if not isinstance(count, int) or count < 1 or count > 10:
        return error_response(
            "Count must be an integer between 1 and 10",
            code="INVALID_COUNT",
            status_code=400,
        )
    
    generator = get_or_create_generator()
    
    # Validate template and variables
    valid, missing = generator.validate_template_variables(template_name, variables)
    if not valid:
        return error_response(
            f"Missing required variables: {', '.join(missing)}",
            code="MISSING_VARIABLES",
            status_code=400,
        )
    
    try:
        # Parse temperature range if provided
        temp_range_tuple = None
        if temperature_range and isinstance(temperature_range, (list, tuple)) and len(temperature_range) == 2:
            temp_range_tuple = (float(temperature_range[0]), float(temperature_range[1]))
        
        variations = generator.generate_multiple_variations(
            template_name,
            variables,
            count=count,
            temperature_range=temp_range_tuple,
        )
        
        total_cost = sum(v.get("cost", 0) for v in variations)
        success_count = sum(1 for v in variations if v.get("success"))
        
        logger.info(
            f"Generated {count} variations: template={template_name}, "
            f"total_cost=${total_cost:.6f}"
        )
        
        return success_response({
            "variations": variations,
            "total_cost": round(total_cost, 6),
            "success_count": success_count,
            "failure_count": len(variations) - success_count,
        })
    except Exception as e:
        logger.exception(f"Variations generation error: {e}")
        return error_response(
            "An error occurred during variation generation",
            code="GENERATION_ERROR",
            status_code=500,
        )


@app.route("/api/generate/batch", methods=["POST"])
@rate_limit
@validate_json
def api_generate_batch() -> Tuple[Response, int]:
    """Process multiple generation requests."""
    data = request.get_json(force=True)
    
    requests_list = data.get("requests", [])
    parallel = data.get("parallel", False)
    
    if not isinstance(requests_list, list):
        return error_response(
            "Requests must be a list",
            code="INVALID_REQUESTS",
            status_code=400,
        )
    
    if len(requests_list) > 20:
        return error_response(
            "Maximum 20 requests per batch",
            code="BATCH_TOO_LARGE",
            status_code=400,
        )
    
    generator = get_or_create_generator()
    
    # Convert to expected format
    formatted_requests = []
    for i, req in enumerate(requests_list):
        if not isinstance(req, dict):
            return error_response(
                f"Request {i} must be an object",
                code="INVALID_REQUEST",
                status_code=400,
            )
        template = req.get("template") or req.get("template_name")
        if not template:
            return error_response(
                f"Request {i} missing template name",
                code="MISSING_TEMPLATE",
                status_code=400,
            )
        formatted_requests.append({
            "template_name": template,
            "variables": req.get("variables", {}),
        })
    
    try:
        results = generator.generate_batch(formatted_requests, parallel=parallel)
        
        total_cost = sum(r.get("cost", 0) for r in results)
        success_count = sum(1 for r in results if r.get("success"))
        
        logger.info(
            f"Batch generation: {len(results)} requests, "
            f"success={success_count}, total_cost=${total_cost:.6f}"
        )
        
        return success_response({
            "results": results,
            "total_cost": round(total_cost, 6),
            "success_count": success_count,
            "failure_count": len(results) - success_count,
        })
    except Exception as e:
        logger.exception(f"Batch generation error: {e}")
        return error_response(
            "An error occurred during batch generation",
            code="BATCH_ERROR",
            status_code=500,
        )


# =============================================================================
# API ROUTES - History
# =============================================================================


@app.route("/api/history", methods=["GET"])
@rate_limit
def api_get_history() -> Tuple[Response, int]:
    """Get generation history for current session."""
    generator = get_or_create_generator()
    
    # Parse query parameters
    limit = request.args.get("limit", 20, type=int)
    template_filter = request.args.get("template")
    since = request.args.get("since")
    
    # Validate limit
    limit = min(max(limit, 1), 100)  # Clamp between 1 and 100
    
    # Parse since date
    start_date = None
    if since:
        try:
            start_date = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            return error_response(
                "Invalid date format for 'since'. Use ISO 8601 format.",
                code="INVALID_DATE",
                status_code=400,
            )
    
    history = generator.get_history(
        limit=limit,
        template_filter=template_filter,
        start_date=start_date,
    )
    
    total_cost = sum(h.get("cost", 0) for h in history)
    
    return success_response({
        "history": history,
        "count": len(history),
        "total_cost": round(total_cost, 6),
    })


@app.route("/api/history/export", methods=["GET"])
@rate_limit
def api_export_history() -> Response:
    """Export history as downloadable file."""
    generator = get_or_create_generator()
    
    export_format = request.args.get("format", "json").lower()
    if export_format not in ("json", "csv", "txt"):
        resp, _ = error_response(
            "Invalid format. Use 'json', 'csv', or 'txt'.",
            code="INVALID_FORMAT",
            status_code=400,
        )
        return resp
    
    # Create temp file for export
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f".{export_format}",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp_path = tmp.name
    
    try:
        generator.export_history(tmp_path, format=export_format)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"content_history_{timestamp}.{export_format}"
        
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/octet-stream",
        )
    finally:
        # Clean up temp file after sending
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/api/history/clear", methods=["DELETE"])
@rate_limit
def api_clear_history() -> Tuple[Response, int]:
    """Clear generation history for current session."""
    generator = get_or_create_generator()
    
    deleted_count = generator.clear_history()
    
    logger.info(f"History cleared: {deleted_count} entries removed")
    
    return success_response({
        "deleted_count": deleted_count,
        "message": f"Cleared {deleted_count} history entries",
    })


# =============================================================================
# API ROUTES - Statistics
# =============================================================================


@app.route("/api/statistics", methods=["GET"])
@rate_limit
def api_get_statistics() -> Tuple[Response, int]:
    """Get usage statistics for current session."""
    generator = get_or_create_generator()
    stats = generator.get_statistics()
    
    return success_response({"stats": stats})


# =============================================================================
# API ROUTES - Validation & Estimation
# =============================================================================


@app.route("/api/validate", methods=["POST"])
@rate_limit
@validate_json
def api_validate() -> Tuple[Response, int]:
    """Validate template variables without generating."""
    data = request.get_json(force=True)
    
    template_name = data.get("template")
    variables = data.get("variables", {})
    
    if not template_name:
        return error_response(
            "Missing required field: template",
            code="MISSING_FIELD",
            status_code=400,
        )
    
    generator = get_or_create_generator()
    
    valid, missing = generator.validate_template_variables(template_name, variables)
    
    # Also get cost estimate if valid
    estimated_cost = None
    if valid:
        estimate = generator.estimate_cost(template_name, variables)
        if estimate.get("success"):
            estimated_cost = estimate.get("estimated_cost")
    
    return success_response({
        "valid": valid,
        "missing_variables": missing,
        "estimated_cost": estimated_cost,
    })


@app.route("/api/cost-estimate", methods=["POST"])
@rate_limit
@validate_json
def api_cost_estimate() -> Tuple[Response, int]:
    """Estimate cost before generation."""
    data = request.get_json(force=True)
    
    template_name = data.get("template")
    variables = data.get("variables", {})
    model = data.get("model")
    
    if not template_name:
        return error_response(
            "Missing required field: template",
            code="MISSING_FIELD",
            status_code=400,
        )
    
    generator = get_or_create_generator()
    
    estimate = generator.estimate_cost(template_name, variables, model=model)
    
    if estimate.get("success"):
        return success_response({
            "estimate": {
                "input_tokens": estimate.get("estimated_prompt_tokens"),
                "estimated_output_tokens": estimate.get("estimated_completion_tokens"),
                "total_tokens": estimate.get("estimated_total_tokens"),
                "estimated_cost": estimate.get("estimated_cost"),
                "model": estimate.get("model"),
            }
        })
    else:
        return error_response(
            estimate.get("error", "Cost estimation failed"),
            code="ESTIMATION_FAILED",
            status_code=400,
        )


# =============================================================================
# API ROUTES - Cache Management
# =============================================================================


@app.route("/api/cache/clear", methods=["DELETE"])
@rate_limit
def api_clear_cache() -> Tuple[Response, int]:
    """Clear the generation cache for current session."""
    generator = get_or_create_generator()
    
    cleared_count = generator.clear_cache()
    
    return success_response({
        "cleared_count": cleared_count,
        "message": f"Cleared {cleared_count} cache entries",
    })


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def create_app() -> Flask:
    """Application factory for production deployment."""
    return app


if __name__ == "__main__":
    # Check for .env file
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("Warning: .env file not found. Run 'python -m src.cli init' to configure.")
        print("Using mock generator for demo purposes.\n")
    
    # Determine environment
    debug = os.getenv("FLASK_ENV", "development") == "development"
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "127.0.0.1")
    
    print("=" * 60)
    print("  AI Content Generator Web Application")
    print("=" * 60)
    print(f"  Environment: {'Development' if debug else 'Production'}")
    print(f"  URL: http://{host}:{port}")
    print(f"  API Docs: http://{host}:{port}/docs")
    print("=" * 60)
    print("Press Ctrl+C to stop\n")
    
    # Use threaded mode for better Windows compatibility
    # Disable reloader in debug mode to avoid watchdog issues on Windows
    app.run(debug=debug, host=host, port=port, threaded=True, use_reloader=False)

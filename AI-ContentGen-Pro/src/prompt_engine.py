"""Production-grade prompt engineering system for AI content generation.

This module implements a robust prompt template management system using
Factory and Template design patterns. It provides thread-safe operations,
template versioning, A/B testing capability, and comprehensive validation.

Example Usage:
    >>> from src.prompt_engine import PromptEngine, PromptTemplate
    >>> 
    >>> # Initialize the engine with built-in templates
    >>> engine = PromptEngine()
    >>> engine.load_templates()
    >>> 
    >>> # List available templates
    >>> templates = engine.list_templates()
    >>> print(f"Available templates: {templates}")
    >>> 
    >>> # Get a specific template
    >>> template = engine.get_template("product_description")
    >>> print(f"Required variables: {template.required_variables}")
    >>> 
    >>> # Generate content from template
    >>> content = template.generate({
    ...     "product_name": "Smart Watch Pro",
    ...     "features": "heart rate monitor, GPS, water resistant",
    ...     "audience": "fitness enthusiasts",
    ...     "tone": "energetic",
    ...     "length": 150
    ... })
    >>> print(content)
    >>> 
    >>> # Create a custom template
    >>> custom = PromptTemplate(
    ...     name="custom_intro",
    ...     category="general",
    ...     template="Write a {tone} introduction about {topic}.",
    ...     system_instructions="You are a helpful writer.",
    ...     required_variables=["topic"],
    ...     optional_variables={"tone": "professional"}
    ... )
    >>> engine.register_template(custom)
    >>> 
    >>> # Clone and customize existing template
    >>> cloned = engine.clone_template("product_description", "my_product_desc")
    >>> cloned.default_tone = "casual"

Author: AI-ContentGen-Pro Team
Version: 1.0.0
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import Enum

# Configure module logger
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Template categories
class TemplateCategory(Enum):
    """Enumeration of template categories."""
    
    MARKETING = "marketing"
    TECHNICAL = "technical"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    SEO = "seo"
    BRANDING = "branding"
    SUPPORT = "support"
    CONTENT = "content"
    GENERAL = "general"


# Tone options
class Tone(Enum):
    """Enumeration of available content tones."""
    
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    CREATIVE = "creative"
    PERSUASIVE = "persuasive"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    ENERGETIC = "energetic"
    HELPFUL = "helpful"
    CONVERSATIONAL = "conversational"
    AUTHORITATIVE = "authoritative"


# Default values
DEFAULT_VERSION: str = "1.0.0"
DEFAULT_MAX_TOKENS: int = 500
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_CACHE_SIZE: int = 128

# Validation patterns
VARIABLE_PATTERN: re.Pattern = re.compile(r"\{(\w+)\}")
DANGEROUS_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?i)(drop|delete|truncate|alter|insert|update)\s+(table|database|schema)", re.IGNORECASE),
    re.compile(r"(?i)<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"(?i)javascript:", re.IGNORECASE),
    re.compile(r"(?i)on\w+\s*=", re.IGNORECASE),
]

# Maximum lengths for validation
MAX_TEMPLATE_LENGTH: int = 10000
MAX_VARIABLE_LENGTH: int = 5000
MAX_NAME_LENGTH: int = 100


# =============================================================================
# EXCEPTIONS
# =============================================================================

class PromptEngineError(Exception):
    """Base exception for prompt engine errors."""
    pass


class TemplateNotFoundError(PromptEngineError):
    """Raised when a requested template does not exist."""
    pass


class TemplateValidationError(PromptEngineError):
    """Raised when template validation fails."""
    pass


class VariableValidationError(PromptEngineError):
    """Raised when variable validation fails."""
    pass


class SanitizationError(PromptEngineError):
    """Raised when input sanitization detects malicious content."""
    pass


# =============================================================================
# PROMPT TEMPLATE CLASS
# =============================================================================

@dataclass
class PromptTemplate:
    """A template for generating AI prompts with variable substitution.
    
    This class implements the Template design pattern, allowing for
    dynamic variable injection into predefined prompt structures.
    
    Attributes:
        name: Unique identifier for the template.
        category: Content type classification (e.g., "marketing", "technical").
        template: The actual prompt template with {variable} placeholders.
        system_instructions: Context/instructions for the AI model.
        default_tone: Default tone for content generation.
        required_variables: List of variables that must be provided.
        optional_variables: Dictionary of variables with default values.
        max_tokens_recommendation: Suggested token limit for generation.
        temperature_recommendation: Suggested creativity level (0.0-2.0).
        version: Template version for tracking changes.
        description: Human-readable description of the template.
        tags: List of tags for searchability.
        ab_test_group: Optional A/B test group identifier.
        enabled: Whether the template is active.
    
    Example:
        >>> template = PromptTemplate(
        ...     name="greeting",
        ...     category="general",
        ...     template="Write a {tone} greeting for {name}.",
        ...     system_instructions="You are a friendly assistant.",
        ...     required_variables=["name"],
        ...     optional_variables={"tone": "warm"}
        ... )
        >>> prompt = template.generate({"name": "Alice"})
        >>> print(prompt)
        'Write a warm greeting for Alice.'
    """
    
    # Required fields
    name: str
    category: str
    template: str
    system_instructions: str
    
    # Optional fields with defaults
    default_tone: str = Tone.PROFESSIONAL.value
    required_variables: List[str] = field(default_factory=list)
    optional_variables: Dict[str, str] = field(default_factory=dict)
    max_tokens_recommendation: int = DEFAULT_MAX_TOKENS
    temperature_recommendation: float = DEFAULT_TEMPERATURE
    version: str = DEFAULT_VERSION
    description: str = ""
    tags: List[str] = field(default_factory=list)
    ab_test_group: Optional[str] = None
    enabled: bool = True
    
    def __post_init__(self) -> None:
        """Validate template after initialization."""
        self._validate_template()
        
    def _validate_template(self) -> None:
        """Validate template structure and values.
        
        Raises:
            TemplateValidationError: If template validation fails.
        """
        # Validate name
        if not self.name or not isinstance(self.name, str):
            raise TemplateValidationError("Template name must be a non-empty string")
        
        if len(self.name) > MAX_NAME_LENGTH:
            raise TemplateValidationError(
                f"Template name exceeds maximum length of {MAX_NAME_LENGTH}"
            )
        
        # Validate template string
        if not self.template or not isinstance(self.template, str):
            raise TemplateValidationError("Template must be a non-empty string")
        
        if len(self.template) > MAX_TEMPLATE_LENGTH:
            raise TemplateValidationError(
                f"Template exceeds maximum length of {MAX_TEMPLATE_LENGTH}"
            )
        
        # Validate temperature
        if not 0.0 <= self.temperature_recommendation <= 2.0:
            raise TemplateValidationError(
                f"Temperature must be between 0.0 and 2.0, got {self.temperature_recommendation}"
            )
        
        # Validate max_tokens
        if self.max_tokens_recommendation < 1:
            raise TemplateValidationError(
                f"max_tokens_recommendation must be at least 1"
            )
        
        # Extract variables from template and validate
        template_vars = set(VARIABLE_PATTERN.findall(self.template))
        required_set = set(self.required_variables)
        optional_set = set(self.optional_variables.keys())
        
        # Check for undeclared variables
        declared_vars = required_set | optional_set
        undeclared = template_vars - declared_vars
        if undeclared:
            logger.warning(
                f"Template '{self.name}' has undeclared variables: {undeclared}. "
                "These will be treated as optional with empty defaults."
            )
        
        # Check for unused declared variables
        unused = declared_vars - template_vars
        if unused:
            logger.warning(
                f"Template '{self.name}' has declared but unused variables: {unused}"
            )
    
    def validate_variables(self, variables: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if all required variables are provided.
        
        Args:
            variables: Dictionary of variable names to values.
            
        Returns:
            Tuple of (is_valid, list_of_missing_variables).
            
        Example:
            >>> template = PromptTemplate(
            ...     name="test",
            ...     category="general",
            ...     template="{a} and {b}",
            ...     system_instructions="Test",
            ...     required_variables=["a", "b"]
            ... )
            >>> is_valid, missing = template.validate_variables({"a": "hello"})
            >>> print(is_valid, missing)
            False ['b']
        """
        if not isinstance(variables, dict):
            return False, ["Variables must be a dictionary"]
        
        missing = []
        for var in self.required_variables:
            if var not in variables or variables[var] is None:
                missing.append(var)
            elif isinstance(variables[var], str) and not variables[var].strip():
                missing.append(var)
        
        return len(missing) == 0, missing
    
    def _sanitize_value(self, value: Any) -> str:
        """Sanitize a variable value to prevent injection attacks.
        
        Args:
            value: The value to sanitize.
            
        Returns:
            Sanitized string value.
            
        Raises:
            SanitizationError: If malicious content is detected.
        """
        # Convert to string
        str_value = str(value) if value is not None else ""
        
        # Check length
        if len(str_value) > MAX_VARIABLE_LENGTH:
            raise SanitizationError(
                f"Variable value exceeds maximum length of {MAX_VARIABLE_LENGTH}"
            )
        
        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(str_value):
                logger.warning(f"Potentially malicious content detected and blocked")
                raise SanitizationError(
                    "Input contains potentially malicious content"
                )
        
        # Basic sanitization - escape curly braces to prevent template injection
        str_value = str_value.replace("{", "{{").replace("}", "}}")
        
        return str_value
    
    def generate(
        self,
        variables: Dict[str, Any],
        sanitize: bool = True,
        include_system: bool = False
    ) -> str:
        """Fill template with provided variables.
        
        Args:
            variables: Dictionary mapping variable names to values.
            sanitize: Whether to sanitize input values (default: True).
            include_system: Whether to prepend system instructions.
            
        Returns:
            The filled template string.
            
        Raises:
            VariableValidationError: If required variables are missing.
            SanitizationError: If malicious content is detected.
            
        Example:
            >>> template = PromptTemplate(
            ...     name="greeting",
            ...     category="general",
            ...     template="Hello {name}, welcome to {place}!",
            ...     system_instructions="Be friendly.",
            ...     required_variables=["name"],
            ...     optional_variables={"place": "our store"}
            ... )
            >>> result = template.generate({"name": "Alice"})
            >>> print(result)
            'Hello Alice, welcome to our store!'
        """
        # Validate required variables
        is_valid, missing = self.validate_variables(variables)
        if not is_valid:
            raise VariableValidationError(
                f"Missing required variables for template '{self.name}': {missing}"
            )
        
        # Merge with optional defaults
        merged_vars: Dict[str, str] = dict(self.optional_variables)
        
        # Add tone default if not provided
        if "tone" not in merged_vars and "tone" not in variables:
            merged_vars["tone"] = self.default_tone
        
        # Override with provided variables
        for key, value in variables.items():
            if sanitize:
                merged_vars[key] = self._sanitize_value(value)
            else:
                merged_vars[key] = str(value) if value is not None else ""
        
        # Perform substitution
        try:
            # Unescape the sanitized values before substitution
            final_vars = {
                k: v.replace("{{", "{").replace("}}", "}") 
                for k, v in merged_vars.items()
            }
            result = self.template.format(**final_vars)
        except KeyError as e:
            raise VariableValidationError(
                f"Template variable {e} not provided and has no default"
            )
        
        # Optionally prepend system instructions
        if include_system and self.system_instructions:
            result = f"[System: {self.system_instructions}]\n\n{result}"
        
        logger.debug(f"Generated prompt from template '{self.name}' v{self.version}")
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize template to dictionary.
        
        Returns:
            Dictionary representation of the template.
            
        Example:
            >>> template = PromptTemplate(
            ...     name="test",
            ...     category="general",
            ...     template="Hello {name}",
            ...     system_instructions="Be nice"
            ... )
            >>> data = template.to_dict()
            >>> print(data["name"])
            'test'
        """
        return {
            "name": self.name,
            "category": self.category,
            "template": self.template,
            "system_instructions": self.system_instructions,
            "default_tone": self.default_tone,
            "required_variables": self.required_variables,
            "optional_variables": self.optional_variables,
            "max_tokens_recommendation": self.max_tokens_recommendation,
            "temperature_recommendation": self.temperature_recommendation,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "ab_test_group": self.ab_test_group,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """Create template from dictionary.
        
        Args:
            data: Dictionary containing template data.
            
        Returns:
            New PromptTemplate instance.
            
        Raises:
            TemplateValidationError: If required fields are missing.
        """
        required_fields = ["name", "category", "template", "system_instructions"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise TemplateValidationError(
                f"Missing required fields for template: {missing}"
            )
        
        return cls(
            name=data["name"],
            category=data["category"],
            template=data["template"],
            system_instructions=data["system_instructions"],
            default_tone=data.get("default_tone", Tone.PROFESSIONAL.value),
            required_variables=data.get("required_variables", []),
            optional_variables=data.get("optional_variables", {}),
            max_tokens_recommendation=data.get("max_tokens_recommendation", DEFAULT_MAX_TOKENS),
            temperature_recommendation=data.get("temperature_recommendation", DEFAULT_TEMPERATURE),
            version=data.get("version", DEFAULT_VERSION),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            ab_test_group=data.get("ab_test_group"),
            enabled=data.get("enabled", True),
        )
    
    def clone(self, new_name: str) -> "PromptTemplate":
        """Create a copy of this template with a new name.
        
        Args:
            new_name: Name for the cloned template.
            
        Returns:
            New PromptTemplate instance.
        """
        data = self.to_dict()
        data["name"] = new_name
        return PromptTemplate.from_dict(data)


# =============================================================================
# PROMPT ENGINE CLASS
# =============================================================================

class PromptEngine:
    """Central management hub for prompt templates.
    
    This class implements the Factory design pattern for creating and
    managing prompt templates. It provides thread-safe operations,
    caching, and comprehensive template management.
    
    Attributes:
        templates: Dictionary of all registered templates.
        active_templates: Set of currently enabled template names.
        
    Example:
        >>> engine = PromptEngine()
        >>> engine.load_templates()
        >>> 
        >>> # Get all marketing templates
        >>> marketing = engine.list_templates(category="marketing")
        >>> 
        >>> # Generate content
        >>> template = engine.get_template("product_description")
        >>> prompt = template.generate({
        ...     "product_name": "Super Widget",
        ...     "features": "fast, reliable, affordable",
        ...     "audience": "small businesses"
        ... })
    """
    
    def __init__(self, cache_size: int = DEFAULT_CACHE_SIZE) -> None:
        """Initialize the prompt engine.
        
        Args:
            cache_size: Maximum number of templates to cache.
        """
        self._templates: Dict[str, PromptTemplate] = {}
        self._active_templates: Set[str] = set()
        self._lock = threading.RLock()
        self._cache_size = cache_size
        self._usage_stats: Dict[str, int] = {}
        
        logger.info("PromptEngine initialized")
    
    @property
    def templates(self) -> Dict[str, PromptTemplate]:
        """Get a copy of all templates."""
        with self._lock:
            return dict(self._templates)
    
    @property
    def active_templates(self) -> Set[str]:
        """Get a copy of active template names."""
        with self._lock:
            return set(self._active_templates)
    
    def load_templates(self) -> None:
        """Initialize all built-in templates.
        
        This method loads the default set of templates for common
        content generation tasks.
        """
        with self._lock:
            builtin_templates = self._create_builtin_templates()
            for template in builtin_templates:
                self._templates[template.name] = template
                if template.enabled:
                    self._active_templates.add(template.name)
            
            logger.info(f"Loaded {len(builtin_templates)} built-in templates")
    
    def _create_builtin_templates(self) -> List[PromptTemplate]:
        """Create the built-in template collection.
        
        Returns:
            List of PromptTemplate instances.
        """
        return [
            # 1. PRODUCT_DESCRIPTION
            PromptTemplate(
                name="product_description",
                category=TemplateCategory.MARKETING.value,
                template=(
                    "Write a {tone} product description for {product_name}. "
                    "Key features: {features}. Target audience: {audience}. "
                    "Length: {length} words. Include a compelling call-to-action."
                ),
                system_instructions="You are an expert e-commerce copywriter",
                default_tone=Tone.PERSUASIVE.value,
                required_variables=["product_name", "features", "audience"],
                optional_variables={"tone": "persuasive", "length": "100"},
                max_tokens_recommendation=300,
                temperature_recommendation=0.7,
                version="1.0.0",
                description="Generate compelling product descriptions for e-commerce",
                tags=["e-commerce", "copywriting", "product", "marketing"],
            ),
            
            # 2. SOCIAL_MEDIA_POST
            PromptTemplate(
                name="social_media_post",
                category=TemplateCategory.SOCIAL_MEDIA.value,
                template=(
                    "Create a {platform}-optimized post about {topic}. "
                    "Tone: {tone}. Include {hashtag_count} relevant hashtags "
                    "and a strong call-to-action: {cta}. "
                    "Character limit: {char_limit}."
                ),
                system_instructions="You are a social media marketing specialist",
                default_tone=Tone.CASUAL.value,
                required_variables=["platform", "topic", "cta"],
                optional_variables={
                    "tone": "engaging",
                    "hashtag_count": "3",
                    "char_limit": "280"
                },
                max_tokens_recommendation=200,
                temperature_recommendation=0.8,
                version="1.0.0",
                description="Create platform-optimized social media posts",
                tags=["social-media", "marketing", "engagement"],
            ),
            
            # 3. EMAIL_SUBJECT_LINE
            PromptTemplate(
                name="email_subject_line",
                category=TemplateCategory.EMAIL.value,
                template=(
                    "Generate {count} email subject lines for {campaign_type}. "
                    "Target audience: {audience}. Goal: {goal}. Style: {style}. "
                    "Each must be under 60 characters and avoid spam trigger words."
                ),
                system_instructions=(
                    "You are an email marketing expert specializing in high open rates"
                ),
                default_tone=Tone.PROFESSIONAL.value,
                required_variables=["campaign_type", "audience", "goal"],
                optional_variables={"count": "5", "style": "professional"},
                max_tokens_recommendation=300,
                temperature_recommendation=0.8,
                version="1.0.0",
                description="Generate high-converting email subject lines",
                tags=["email", "marketing", "conversion", "subject-lines"],
            ),
            
            # 4. BLOG_POST_OUTLINE
            PromptTemplate(
                name="blog_post_outline",
                category=TemplateCategory.CONTENT.value,
                template=(
                    'Create a detailed blog post outline for: "{title}". '
                    "Target keyword: {keyword}. Audience: {audience}. "
                    "Include {section_count} main sections with subsections. "
                    "Add meta description and suggested internal links."
                ),
                system_instructions="You are a content strategist and SEO specialist",
                default_tone=Tone.AUTHORITATIVE.value,
                required_variables=["title", "keyword", "audience"],
                optional_variables={"section_count": "5"},
                max_tokens_recommendation=800,
                temperature_recommendation=0.6,
                version="1.0.0",
                description="Create SEO-optimized blog post outlines",
                tags=["blog", "seo", "content-strategy", "outline"],
            ),
            
            # 5. META_DESCRIPTION
            PromptTemplate(
                name="meta_description",
                category=TemplateCategory.SEO.value,
                template=(
                    "Write an SEO-optimized meta description for a page about {topic}. "
                    "Primary keyword: {keyword}. Include a call-to-action. "
                    "Must be 150-160 characters and compelling for search results."
                ),
                system_instructions="You are an SEO specialist",
                default_tone=Tone.PROFESSIONAL.value,
                required_variables=["topic", "keyword"],
                optional_variables={},
                max_tokens_recommendation=100,
                temperature_recommendation=0.5,
                version="1.0.0",
                description="Generate SEO-optimized meta descriptions",
                tags=["seo", "meta-description", "search"],
            ),
            
            # 6. TAGLINE_SLOGAN
            PromptTemplate(
                name="tagline_slogan",
                category=TemplateCategory.BRANDING.value,
                template=(
                    "Generate {count} memorable taglines for {brand_name}. "
                    "Industry: {industry}. Brand personality: {personality}. "
                    "Target emotion: {emotion}. "
                    "Each must be under 10 words and unique."
                ),
                system_instructions="You are a creative branding expert",
                default_tone=Tone.CREATIVE.value,
                required_variables=["brand_name", "industry", "personality", "emotion"],
                optional_variables={"count": "5"},
                max_tokens_recommendation=250,
                temperature_recommendation=0.9,
                version="1.0.0",
                description="Generate memorable brand taglines and slogans",
                tags=["branding", "tagline", "slogan", "creative"],
            ),
            
            # 7. FAQ_GENERATOR
            PromptTemplate(
                name="faq_generator",
                category=TemplateCategory.SUPPORT.value,
                template=(
                    "Generate {count} frequently asked questions and detailed answers "
                    "for {product_or_service}. Target audience: {audience}. "
                    "Tone: {tone}. Focus on common concerns about {focus_area}."
                ),
                system_instructions="You are a customer support expert",
                default_tone=Tone.HELPFUL.value,
                required_variables=["product_or_service", "audience", "focus_area"],
                optional_variables={"tone": "helpful", "count": "5"},
                max_tokens_recommendation=1000,
                temperature_recommendation=0.5,
                version="1.0.0",
                description="Generate comprehensive FAQ content",
                tags=["faq", "support", "customer-service", "documentation"],
            ),
            
            # 8. EMAIL_NEWSLETTER
            PromptTemplate(
                name="email_newsletter",
                category=TemplateCategory.EMAIL.value,
                template=(
                    "Write an engaging email newsletter about {topic}. "
                    "Target: {audience}. Include: attention-grabbing subject line, "
                    "opening hook, {section_count} content sections, and clear CTA: {cta}. "
                    "Tone: {tone}."
                ),
                system_instructions="You are an email marketing copywriter",
                default_tone=Tone.CONVERSATIONAL.value,
                required_variables=["topic", "audience", "cta"],
                optional_variables={
                    "section_count": "3",
                    "tone": "conversational"
                },
                max_tokens_recommendation=800,
                temperature_recommendation=0.7,
                version="1.0.0",
                description="Create engaging email newsletter content",
                tags=["email", "newsletter", "marketing", "engagement"],
            ),
            
            # 9. PRESS_RELEASE (Bonus template)
            PromptTemplate(
                name="press_release",
                category=TemplateCategory.MARKETING.value,
                template=(
                    "Write a professional press release for {company_name} announcing {announcement}. "
                    "Include: headline, subheadline, dateline ({location}), lead paragraph, "
                    "{body_paragraph_count} body paragraphs, boilerplate, and contact info placeholder. "
                    "Tone: {tone}. Target media: {target_media}."
                ),
                system_instructions="You are a PR and communications specialist",
                default_tone=Tone.FORMAL.value,
                required_variables=["company_name", "announcement", "location"],
                optional_variables={
                    "body_paragraph_count": "3",
                    "tone": "formal",
                    "target_media": "general news outlets"
                },
                max_tokens_recommendation=800,
                temperature_recommendation=0.4,
                version="1.0.0",
                description="Generate professional press releases",
                tags=["pr", "press-release", "communications", "announcement"],
            ),
            
            # 10. COMPETITOR_ANALYSIS (Bonus template)
            PromptTemplate(
                name="competitor_analysis",
                category=TemplateCategory.MARKETING.value,
                template=(
                    "Create a competitive analysis comparing {company} to competitors: {competitors}. "
                    "Industry: {industry}. Focus areas: {focus_areas}. "
                    "Include: strengths, weaknesses, opportunities, and threats for each. "
                    "Analysis depth: {depth}."
                ),
                system_instructions="You are a market research and competitive intelligence analyst",
                default_tone=Tone.AUTHORITATIVE.value,
                required_variables=["company", "competitors", "industry", "focus_areas"],
                optional_variables={"depth": "comprehensive"},
                max_tokens_recommendation=1500,
                temperature_recommendation=0.4,
                version="1.0.0",
                description="Generate competitive analysis reports",
                tags=["analysis", "competition", "market-research", "strategy"],
            ),
        ]
    
    @lru_cache(maxsize=DEFAULT_CACHE_SIZE)
    def _get_template_cached(self, name: str) -> Optional[Dict[str, Any]]:
        """Cache layer for template retrieval.
        
        Note: Returns dict to allow LRU caching (dataclass not hashable).
        """
        template = self._templates.get(name)
        if template:
            return template.to_dict()
        return None
    
    def get_template(self, name: str, use_cache: bool = True) -> PromptTemplate:
        """Retrieve a template by name.
        
        Args:
            name: The template name to retrieve.
            use_cache: Whether to use cached template (default: True).
            
        Returns:
            The requested PromptTemplate.
            
        Raises:
            TemplateNotFoundError: If template does not exist.
            
        Example:
            >>> engine = PromptEngine()
            >>> engine.load_templates()
            >>> template = engine.get_template("product_description")
            >>> print(template.category)
            'marketing'
        """
        with self._lock:
            if name not in self._templates:
                raise TemplateNotFoundError(f"Template '{name}' not found")
            
            # Track usage for analytics
            self._usage_stats[name] = self._usage_stats.get(name, 0) + 1
            
            if use_cache:
                cached = self._get_template_cached(name)
                if cached:
                    return PromptTemplate.from_dict(cached)
            
            return self._templates[name]
    
    def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        enabled_only: bool = True
    ) -> List[str]:
        """List available templates, optionally filtered.
        
        Args:
            category: Filter by category (e.g., "marketing").
            tags: Filter by tags (templates must have all specified tags).
            enabled_only: Only return enabled templates (default: True).
            
        Returns:
            List of template names matching the criteria.
            
        Example:
            >>> engine = PromptEngine()
            >>> engine.load_templates()
            >>> marketing_templates = engine.list_templates(category="marketing")
            >>> print(marketing_templates)
            ['product_description', 'press_release', 'competitor_analysis']
        """
        with self._lock:
            results = []
            
            for name, template in self._templates.items():
                # Filter by enabled status
                if enabled_only and not template.enabled:
                    continue
                
                # Filter by category
                if category and template.category != category:
                    continue
                
                # Filter by tags (must have all specified tags)
                if tags:
                    template_tags = set(template.tags)
                    if not all(tag in template_tags for tag in tags):
                        continue
                
                results.append(name)
            
            return sorted(results)
    
    def list_categories(self) -> List[str]:
        """List all unique template categories.
        
        Returns:
            Sorted list of category names.
        """
        with self._lock:
            categories = set(t.category for t in self._templates.values())
            return sorted(categories)
    
    def register_template(self, template: PromptTemplate) -> None:
        """Add or update a template.
        
        Args:
            template: The PromptTemplate to register.
            
        Raises:
            TemplateValidationError: If template is invalid.
            
        Example:
            >>> engine = PromptEngine()
            >>> custom = PromptTemplate(
            ...     name="my_template",
            ...     category="custom",
            ...     template="Write about {topic}",
            ...     system_instructions="Be helpful"
            ... )
            >>> engine.register_template(custom)
        """
        if not isinstance(template, PromptTemplate):
            raise TemplateValidationError(
                "Template must be a PromptTemplate instance"
            )
        
        with self._lock:
            is_update = template.name in self._templates
            self._templates[template.name] = template
            
            if template.enabled:
                self._active_templates.add(template.name)
            elif template.name in self._active_templates:
                self._active_templates.discard(template.name)
            
            # Invalidate cache for this template
            self._get_template_cached.cache_clear()
            
            action = "Updated" if is_update else "Registered"
            logger.info(f"{action} template '{template.name}' v{template.version}")
    
    def remove_template(self, name: str) -> bool:
        """Remove a template by name.
        
        Args:
            name: The template name to remove.
            
        Returns:
            True if removed, False if not found.
            
        Example:
            >>> engine = PromptEngine()
            >>> engine.load_templates()
            >>> engine.remove_template("product_description")
            True
        """
        with self._lock:
            if name not in self._templates:
                logger.warning(f"Attempted to remove non-existent template '{name}'")
                return False
            
            del self._templates[name]
            self._active_templates.discard(name)
            self._get_template_cached.cache_clear()
            
            logger.info(f"Removed template '{name}'")
            return True
    
    def clone_template(
        self,
        name: str,
        new_name: str,
        updates: Optional[Dict[str, Any]] = None
    ) -> PromptTemplate:
        """Duplicate a template with optional modifications.
        
        Args:
            name: Name of the template to clone.
            new_name: Name for the new template.
            updates: Optional dictionary of field updates.
            
        Returns:
            The newly created PromptTemplate.
            
        Raises:
            TemplateNotFoundError: If source template not found.
            TemplateValidationError: If new_name already exists.
            
        Example:
            >>> engine = PromptEngine()
            >>> engine.load_templates()
            >>> cloned = engine.clone_template(
            ...     "product_description",
            ...     "my_product_desc",
            ...     {"default_tone": "casual"}
            ... )
        """
        with self._lock:
            if name not in self._templates:
                raise TemplateNotFoundError(f"Template '{name}' not found")
            
            if new_name in self._templates:
                raise TemplateValidationError(
                    f"Template '{new_name}' already exists"
                )
            
            # Clone the template
            source = self._templates[name]
            cloned = source.clone(new_name)
            
            # Apply updates if provided
            if updates:
                for key, value in updates.items():
                    if hasattr(cloned, key):
                        setattr(cloned, key, value)
            
            # Register the clone
            self._templates[new_name] = cloned
            if cloned.enabled:
                self._active_templates.add(new_name)
            
            logger.info(f"Cloned template '{name}' to '{new_name}'")
            return cloned
    
    def enable_template(self, name: str) -> bool:
        """Enable a template for use.
        
        Args:
            name: The template name to enable.
            
        Returns:
            True if enabled, False if not found.
        """
        with self._lock:
            if name not in self._templates:
                return False
            
            self._templates[name].enabled = True
            self._active_templates.add(name)
            logger.debug(f"Enabled template '{name}'")
            return True
    
    def disable_template(self, name: str) -> bool:
        """Disable a template from use.
        
        Args:
            name: The template name to disable.
            
        Returns:
            True if disabled, False if not found.
        """
        with self._lock:
            if name not in self._templates:
                return False
            
            self._templates[name].enabled = False
            self._active_templates.discard(name)
            logger.debug(f"Disabled template '{name}'")
            return True
    
    def validate_template_syntax(self, template_str: str) -> Tuple[bool, List[str]]:
        """Check if a template string has valid syntax.
        
        Args:
            template_str: The template string to validate.
            
        Returns:
            Tuple of (is_valid, list_of_issues).
            
        Example:
            >>> engine = PromptEngine()
            >>> is_valid, issues = engine.validate_template_syntax("Hello {name}")
            >>> print(is_valid, issues)
            True []
        """
        issues = []
        
        if not template_str:
            issues.append("Template string is empty")
            return False, issues
        
        if len(template_str) > MAX_TEMPLATE_LENGTH:
            issues.append(f"Template exceeds maximum length of {MAX_TEMPLATE_LENGTH}")
        
        # Check for balanced braces
        open_count = template_str.count("{")
        close_count = template_str.count("}")
        
        if open_count != close_count:
            issues.append(
                f"Unbalanced braces: {open_count} opening, {close_count} closing"
            )
        
        # Extract and validate variable names
        variables = VARIABLE_PATTERN.findall(template_str)
        
        for var in variables:
            if not var.isidentifier():
                issues.append(f"Invalid variable name: '{var}'")
        
        # Check for nested braces (not supported)
        if re.search(r"\{[^}]*\{", template_str):
            issues.append("Nested braces are not supported")
        
        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(template_str):
                issues.append("Template contains potentially dangerous content")
                break
        
        return len(issues) == 0, issues
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get template usage statistics.
        
        Returns:
            Dictionary mapping template names to usage counts.
        """
        with self._lock:
            return dict(self._usage_stats)
    
    def get_template_info(self, name: str) -> Dict[str, Any]:
        """Get comprehensive information about a template.
        
        Args:
            name: The template name.
            
        Returns:
            Dictionary with template details and usage stats.
            
        Raises:
            TemplateNotFoundError: If template not found.
        """
        with self._lock:
            if name not in self._templates:
                raise TemplateNotFoundError(f"Template '{name}' not found")
            
            template = self._templates[name]
            info = template.to_dict()
            info["usage_count"] = self._usage_stats.get(name, 0)
            info["is_active"] = name in self._active_templates
            
            return info
    
    def search_templates(
        self,
        query: str,
        fields: Optional[List[str]] = None
    ) -> List[str]:
        """Search templates by text query.
        
        Args:
            query: Search query string.
            fields: Fields to search (default: name, description, tags).
            
        Returns:
            List of matching template names.
        """
        if fields is None:
            fields = ["name", "description", "tags"]
        
        query_lower = query.lower()
        matches = []
        
        with self._lock:
            for name, template in self._templates.items():
                for field in fields:
                    value = getattr(template, field, None)
                    
                    if value is None:
                        continue
                    
                    if isinstance(value, str):
                        if query_lower in value.lower():
                            matches.append(name)
                            break
                    elif isinstance(value, list):
                        if any(query_lower in str(v).lower() for v in value):
                            matches.append(name)
                            break
        
        return sorted(matches)
    
    def export_templates(self, names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Export templates as list of dictionaries.
        
        Args:
            names: Specific template names to export (default: all).
            
        Returns:
            List of template dictionaries.
        """
        with self._lock:
            if names is None:
                names = list(self._templates.keys())
            
            return [
                self._templates[name].to_dict()
                for name in names
                if name in self._templates
            ]
    
    def import_templates(
        self,
        templates_data: List[Dict[str, Any]],
        overwrite: bool = False
    ) -> Tuple[int, int]:
        """Import templates from list of dictionaries.
        
        Args:
            templates_data: List of template dictionaries.
            overwrite: Whether to overwrite existing templates.
            
        Returns:
            Tuple of (imported_count, skipped_count).
        """
        imported = 0
        skipped = 0
        
        with self._lock:
            for data in templates_data:
                try:
                    name = data.get("name", "")
                    
                    if name in self._templates and not overwrite:
                        logger.debug(f"Skipped existing template '{name}'")
                        skipped += 1
                        continue
                    
                    template = PromptTemplate.from_dict(data)
                    self.register_template(template)
                    imported += 1
                    
                except (TemplateValidationError, KeyError) as e:
                    logger.warning(f"Failed to import template: {e}")
                    skipped += 1
        
        logger.info(f"Imported {imported} templates, skipped {skipped}")
        return imported, skipped


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_template(
    name: str,
    template: str,
    category: str = TemplateCategory.GENERAL.value,
    system_instructions: str = "You are a helpful assistant.",
    required_variables: Optional[List[str]] = None,
    optional_variables: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> PromptTemplate:
    """Factory function to create a PromptTemplate with sensible defaults.
    
    Args:
        name: Unique template identifier.
        template: Template string with {variable} placeholders.
        category: Template category.
        system_instructions: AI model context.
        required_variables: List of required variable names.
        optional_variables: Dict of optional variables with defaults.
        **kwargs: Additional PromptTemplate attributes.
        
    Returns:
        New PromptTemplate instance.
        
    Example:
        >>> template = create_template(
        ...     name="simple_greeting",
        ...     template="Say hello to {name}!",
        ...     required_variables=["name"]
        ... )
    """
    return PromptTemplate(
        name=name,
        category=category,
        template=template,
        system_instructions=system_instructions,
        required_variables=required_variables or [],
        optional_variables=optional_variables or {},
        **kwargs
    )


def create_engine_with_defaults() -> PromptEngine:
    """Factory function to create a fully initialized PromptEngine.
    
    Returns:
        PromptEngine with all built-in templates loaded.
        
    Example:
        >>> engine = create_engine_with_defaults()
        >>> templates = engine.list_templates()
        >>> print(f"Loaded {len(templates)} templates")
    """
    engine = PromptEngine()
    engine.load_templates()
    return engine

# Template Development Guide

## Overview

This guide covers creating custom templates for AI-ContentGen-Pro. Templates use a simple string-based variable substitution system combined with system instructions for AI behavior.

## Table of Contents

- [Template Structure](#template-structure)
- [Creating Templates](#creating-templates)
- [Variable System](#variable-system)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [Testing Templates](#testing-templates)

---

## Template Structure

A template consists of:

1. **Name** - Unique identifier (snake_case)
2. **Description** - Brief explanation of the template's purpose
3. **Category** - Grouping label (content, marketing, seo, etc.)
4. **System Instructions** - AI behavior guidelines
5. **Required Variables** - User must provide these
6. **Optional Variables** - Default values provided

### Template Object

```python
{
    "name": "my_template",
    "description": "Brief description",
    "category": "content",
    "system_instructions": "You are an expert...",
    "required_variables": ["topic", "audience"],
    "optional_variables": {
        "tone": "professional",
        "length": "medium"
    }
}
```

---

## Creating Templates

### Method 1: Register Programmatically

```python
from src.prompt_engine import PromptEngine, PromptTemplate

# Initialize engine
engine = PromptEngine()

# Create template
template = PromptTemplate(
    name="tutorial_creator",
    description="Create step-by-step tutorials",
    category="education",
    system_instructions="""You are an experienced technical writer creating clear, 
    step-by-step tutorials for ${skill_level} learners.""",
    required_variables=["topic", "skill_level"],
    optional_variables={"format": "numbered list", "examples": "include code examples"}
)

# Register template
engine.register_template(template)
```

### Method 2: Add to Built-in Templates

Edit `src/prompt_engine.py` and add to `_create_builtin_templates()`:

```python
def _create_builtin_templates(self) -> List[PromptTemplate]:
    """Create the built-in template collection."""
    templates = [
        # ... existing templates ...
        
        PromptTemplate(
            name="your_new_template",
            description="What it does",
            category="category_name",
            system_instructions="""
            You are an expert in [domain].
            Create [output_type] for ${audience} that:
            1. [Requirement 1]
            2. [Requirement 2]
            3. [Requirement 3]
            
            Focus on ${focus_area}.
            Tone: ${tone}
            """,
            required_variables=["audience", "focus_area"],
            optional_variables={
                "tone": "professional and friendly",
                "length": "medium (300-500 words)"
            }
        ),
    ]
    return templates
```

---

## Variable System

### Variable Syntax

Variables use `${variable_name}` syntax in system instructions:

```python
system_instructions = """
Create content about ${topic} for ${audience}.
Tone: ${tone}
Focus: ${focus_area}
"""
```

### Required Variables

Users **must** provide these values:

```python
required_variables = ["topic", "audience", "keyword"]
```

### Optional Variables

Provide sensible defaults:

```python
optional_variables = {
    "tone": "professional and approachable",
    "length": "medium (300-500 words)",
    "format": "markdown with headers",
    "style": "conversational yet informative"
}
```

### Variable Guidelines

1. **Use descriptive names**: `target_audience` not `ta`
2. **Keep it simple**: Avoid nested or complex variables
3. **Provide examples**: Help users understand what to provide
4. **Set good defaults**: Optional variables should work without changes

---

## Best Practices

### 1. Clear System Instructions

```python
# Good ✓
system_instructions = """
You are an expert ${industry} content creator.

Task: Create a ${content_type} about ${topic} for ${audience}.

Requirements:
1. Start with an engaging hook
2. Include ${key_points} main points
3. End with a clear call-to-action
4. Use ${tone} tone throughout

Keep it ${length}.
Format: ${format}
"""

# Bad ✗
system_instructions = """
Write something about ${topic}.
"""
```

### 2. Specific Requirements

```python
# Good ✓
system_instructions = """
Create a product description that:
- Highlights 3-5 key features
- Addresses pain points
- Includes social proof elements
- Ends with urgency-based CTA
- Uses ${tone} tone
- Length: ${length} words
"""

# Bad ✗
system_instructions = """
Write a product description for ${product}.
"""
```

### 3. Target Audience Context

```python
# Good ✓
system_instructions = """
You are writing for ${audience}.
Consider their:
- Knowledge level: ${skill_level}
- Pain points: ${pain_points}
- Goals: ${goals}
- Preferred tone: ${tone}
"""

# Bad ✗
system_instructions = """
Write for ${audience}.
"""
```

### 4. Output Format Specification

```python
# Good ✓
system_instructions = """
Format the output as:
1. Headline (10 words max)
2. Introduction (2-3 sentences)
3. Main content (3 paragraphs)
4. Conclusion with CTA

Use markdown formatting with ## headers.
"""

# Bad ✗
system_instructions = """
Write some content.
"""
```

---

## Examples

### Example 1: Tutorial Template

```python
PromptTemplate(
    name="technical_tutorial",
    description="Create detailed technical tutorials with code examples",
    category="education",
    system_instructions="""
    You are an experienced software engineering instructor creating tutorials 
    for ${skill_level} developers learning ${technology}.
    
    Create a comprehensive tutorial on "${topic}" that includes:
    
    1. **Introduction**
       - What will be learned
       - Prerequisites
       - Estimated completion time: ${duration}
    
    2. **Step-by-Step Instructions**
       - Clear, numbered steps
       - Code examples for each step
       - Common pitfalls to avoid
    
    3. **Practical Example**
       - Real-world use case
       - Complete working code
       - Expected output
    
    4. **Summary**
       - Key takeaways
       - Next steps for learning
    
    Tone: ${tone}
    Include code comments explaining each section.
    Format: Markdown with syntax highlighting
    """,
    required_variables=["topic", "technology", "skill_level"],
    optional_variables={
        "duration": "30 minutes",
        "tone": "friendly and encouraging"
    }
)
```

### Example 2: Landing Page Copy

```python
PromptTemplate(
    name="landing_page_copy",
    description="Create high-converting landing page copy",
    category="marketing",
    system_instructions="""
    You are a conversion copywriter creating landing page copy for ${product_name}.
    
    Target Audience: ${target_audience}
    Unique Value Proposition: ${usp}
    Key Benefits: ${benefits}
    
    Create landing page sections:
    
    1. **Hero Section**
       - Attention-grabbing headline
       - Sub-headline explaining the benefit
       - Primary CTA button text
    
    2. **Problem Statement**
       - Identify ${num_pain_points} pain points
       - Empathize with the audience
    
    3. **Solution Overview**
       - How ${product_name} solves these problems
       - Key features and benefits
    
    4. **Social Proof**
       - Testimonial template
       - Trust indicators
    
    5. **Final CTA Section**
       - Urgency element
       - Risk reversal
       - Clear call-to-action
    
    Tone: ${tone}
    Focus on benefits over features.
    Use emotional triggers: ${emotions}
    """,
    required_variables=["product_name", "target_audience", "usp", "benefits"],
    optional_variables={
        "tone": "confident and persuasive",
        "num_pain_points": "3",
        "emotions": "fear of missing out, desire for improvement"
    }
)
```

### Example 3: Email Sequence

```python
PromptTemplate(
    name="email_drip_sequence",
    description="Create automated email sequences for nurturing leads",
    category="marketing",
    system_instructions="""
    You are an email marketing expert creating a ${sequence_type} email 
    sequence for ${business_type} targeting ${audience}.
    
    Create Email ${email_number} of ${total_emails}:
    
    **Purpose**: ${email_purpose}
    **Goal**: ${conversion_goal}
    
    Structure:
    1. **Subject Line**
       - Curiosity-driven
       - Personalized
       - Under 50 characters
    
    2. **Preview Text**
       - Complements subject line
       - 40-100 characters
    
    3. **Email Body**
       - Personal greeting
       - Value-first content about ${topic}
       - Story or case study
       - Clear next step
    
    4. **P.S. Section**
       - Additional value or urgency
    
    Tone: ${tone}
    Keep it conversational and scannable.
    CTAs should be benefit-focused.
    Length: ${length} words
    """,
    required_variables=["sequence_type", "business_type", "audience", 
                        "email_number", "total_emails", "email_purpose", 
                        "conversion_goal", "topic"],
    optional_variables={
        "tone": "warm and personal",
        "length": "300"
    }
)
```

---

## Testing Templates

### Unit Test Example

```python
def test_custom_template():
    """Test custom template rendering and generation."""
    from src.prompt_engine import PromptEngine, PromptTemplate
    from src.content_generator import ContentGenerator
    
    # Create engine and register template
    engine = PromptEngine()
    template = PromptTemplate(
        name="test_template",
        description="Test template",
        category="test",
        system_instructions="Create ${content_type} about ${topic}.",
        required_variables=["content_type", "topic"],
        optional_variables={"tone": "professional"}
    )
    engine.register_template(template)
    
    # Test template exists
    assert "test_template" in engine.list_templates()
    
    # Test rendering
    rendered = engine.render_template(
        "test_template",
        {"content_type": "tutorial", "topic": "Python"}
    )
    assert "tutorial" in rendered
    assert "Python" in rendered
    
    # Test with ContentGenerator (requires API key)
    generator = ContentGenerator(prompt_engine=engine)
    result = generator.generate(
        "test_template",
        {"content_type": "article", "topic": "AI"},
        max_tokens=100
    )
    assert result['success']
    assert result['content']
```

### Manual Testing

```python
# test_my_template.py
from src.prompt_engine import PromptEngine, PromptTemplate
from src.content_generator import ContentGenerator

# Register your template
engine = PromptEngine()
# ... register template ...

# Test with real generation
generator = ContentGenerator(prompt_engine=engine)

result = generator.generate(
    template_name="your_template_name",
    variables={
        "required_var1": "value1",
        "required_var2": "value2"
    },
    temperature=0.7,
    max_tokens=500
)

print(result['content'])
print(f"Cost: ${result['cost']:.6f}")
print(f"Tokens: {result['tokens_used']['total']}")
```

---

## Template Categories

Organize templates by category:

- **content** - General content creation (blogs, articles)
- **marketing** - Marketing copy (ads, landing pages)
- **social_media** - Social platform content
- **seo** - SEO-focused content (meta descriptions)
- **email** - Email marketing
- **ecommerce** - Product descriptions, reviews
- **support** - FAQs, documentation
- **branding** - Taglines, mission statements
- **research** - Competitive analysis, reports
- **education** - Tutorials, guides

---

## Variable Naming Conventions

| Good Names | Bad Names |
|------------|-----------|
| `target_audience` | `ta`, `aud` |
| `product_name` | `prod`, `p` |
| `key_features` | `features`, `kf` |
| `call_to_action` | `cta`, `action` |
| `skill_level` | `level`, `skill` |
| `content_length` | `len`, `size` |

---

## Template Validation

Before submitting a template, verify:

- [ ] Unique, descriptive name (snake_case)
- [ ] Clear, concise description
- [ ] Appropriate category
- [ ] Detailed system instructions
- [ ] All variables documented
- [ ] Sensible default values for optional variables
- [ ] No typos or grammar errors in instructions
- [ ] Tested with real API calls
- [ ] Produces expected output format
- [ ] Variable names are clear and descriptive

---

## Contributing Templates

To contribute a new template:

1. **Create** the template following this guide
2. **Test** thoroughly with various inputs
3. **Document** in a PR with:
   - Template purpose and use cases
   - Example inputs and outputs
   - Any special considerations
4. **Add tests** in `tests/test_custom_templates.py`
5. **Update** documentation

See [CONTRIBUTING.md](../CONTRIBUTING.md) for more details.

---

## Advanced Tips

### 1. Context Building

Provide rich context for better outputs:

```python
system_instructions = """
Context: ${industry} industry targeting ${audience}
Market position: ${positioning}
Brand voice: ${brand_voice}
Competitive advantage: ${advantage}

Create ${content_type} that emphasizes these unique points.
"""
```

### 2. Output Constraints

Set clear boundaries:

```python
system_instructions = """
Create content with:
- Word count: ${min_words}-${max_words} words
- Reading level: ${reading_level}
- Keyword density: ${keyword} appears ${density}%
- Headers: Use H2 and H3 only
- Links: Include ${num_links} internal links
"""
```

### 3. Style Guidelines

Enforce consistent style:

```python
system_instructions = """
Writing style:
- Sentence length: Average ${avg_sentence_length} words
- Paragraph length: ${paragraph_length} sentences
- Use active voice: ${active_voice_percent}%
- Include transition words
- Vary sentence structure
Tone: ${tone}
Voice: ${voice}
"""
```

---

## Troubleshooting

### Problem: Variable not substituting

```python
# Wrong
system_instructions = "Create content about {topic}"  # Wrong bracket type

# Correct
system_instructions = "Create content about ${topic}"  # Correct: ${}
```

### Problem: Inconsistent output

```python
# Too vague
system_instructions = "Write something good."

# Better: Be specific
system_instructions = """
Create a 300-word article with:
1. Introduction (50 words)
2. Main content (200 words, 3 paragraphs)
3. Conclusion (50 words with CTA)
"""
```

### Problem: Missing context

```python
# Insufficient context
system_instructions = "Write for ${audience}."

# Better: Provide context
system_instructions = """
Target audience: ${audience}
Their needs: ${needs}
Their pain points: ${pain_points}
Their knowledge level: ${knowledge_level}

Create content that addresses their specific situation.
"""
```

---

## Resources

- [OpenAI Best Practices](https://platform.openai.com/docs/guides/prompt-engineering)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [Example Templates](../examples/custom_templates/)
- [Template Test Suite](../tests/test_prompt_engine.py)

---

## Questions?

- Check [docs/API_GUIDE.md](API_GUIDE.md) for API details
- See [examples/](../examples/) for more examples
- Open an issue on GitHub
- Join our Discord community

#!/usr/bin/env python3
"""Demo script showcasing the production-grade prompt engineering system.

This script demonstrates:
- Loading and listing templates
- Generating content from templates
- Creating custom templates
- Template cloning and customization
- Searching and filtering templates
"""

import sys
import os

# Add project root to path for demo purposes
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.prompt_engine import (
    PromptEngine,
    PromptTemplate,
    TemplateCategory,
    Tone,
    create_template,
    create_engine_with_defaults,
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def main():
    """Demonstrate the prompt engineering system."""
    print_section("AI-ContentGen-Pro Prompt Engine Demo")
    
    # Create engine with built-in templates
    engine = create_engine_with_defaults()
    
    # 1. List all templates
    print_section("1. Available Templates")
    templates = engine.list_templates()
    print(f"Total templates: {len(templates)}\n")
    
    for name in templates:
        info = engine.get_template_info(name)
        print(f"  * {name}")
        print(f"     Category: {info['category']}")
        print(f"     Description: {info.get('description', 'N/A')[:60]}...")
        print(f"     Required: {', '.join(info['required_variables'])}")
        print()
    
    # 2. List templates by category
    print_section("2. Templates by Category")
    categories = engine.list_categories()
    for category in categories:
        cat_templates = engine.list_templates(category=category)
        print(f"  {category}: {len(cat_templates)} templates")
        for t in cat_templates:
            print(f"    - {t}")
    
    # 3. Generate content from template
    print_section("3. Generate Product Description")
    template = engine.get_template("product_description")
    
    print(f"Template: {template.name}")
    print(f"Required variables: {template.required_variables}")
    print(f"Optional variables: {list(template.optional_variables.keys())}")
    print()
    
    prompt = template.generate({
        "product_name": "Smart Watch Pro X",
        "features": "heart rate monitor, GPS tracking, 10-day battery, water resistant",
        "audience": "fitness enthusiasts and busy professionals",
        "tone": "energetic",
        "length": "120"
    })
    
    print("Generated prompt:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)
    
    # 4. Generate social media post
    print_section("4. Generate Social Media Post")
    social_template = engine.get_template("social_media_post")
    
    social_prompt = social_template.generate({
        "platform": "LinkedIn",
        "topic": "AI productivity tools for developers",
        "cta": "Share your favorite AI tools below!",
        "tone": "professional",
        "hashtag_count": "4"
    })
    
    print("Generated social media prompt:")
    print("-" * 40)
    print(social_prompt)
    print("-" * 40)
    
    # 5. Create custom template
    print_section("5. Create Custom Template")
    custom = create_template(
        name="code_review",
        template=(
            "Perform a code review for the following {language} code. "
            "Focus on: {focus_areas}. "
            "Severity level for issues: {severity}. "
            "Include specific line references and suggestions."
        ),
        category=TemplateCategory.TECHNICAL.value,
        system_instructions="You are a senior software engineer performing code reviews.",
        required_variables=["language", "focus_areas"],
        optional_variables={"severity": "all levels"},
        temperature_recommendation=0.3,
        tags=["code", "review", "technical"]
    )
    
    engine.register_template(custom)
    print(f"[OK] Registered custom template: {custom.name}")
    print(f"   Category: {custom.category}")
    print(f"   Tags: {custom.tags}")
    
    # 6. Clone and customize template
    print_section("6. Clone Template")
    cloned = engine.clone_template(
        "product_description",
        "luxury_product_description",
        updates={
            "default_tone": "sophisticated",
            "description": "Premium product descriptions for luxury brands"
        }
    )
    print(f"[OK] Cloned template: {cloned.name}")
    print(f"   Default tone: {cloned.default_tone}")
    print(f"   Description: {cloned.description}")
    
    # 7. Search templates
    print_section("7. Search Templates")
    
    search_queries = ["email", "marketing", "seo"]
    for query in search_queries:
        results = engine.search_templates(query)
        print(f"Search '{query}': {results}")
    
    # 8. Template validation
    print_section("8. Template Syntax Validation")
    
    test_templates = [
        ("Valid template", "Hello {name}, welcome to {place}!"),
        ("Unbalanced braces", "Hello {name, welcome!"),
        ("Invalid variable", "Hello {123invalid}!"),
    ]
    
    for description, template_str in test_templates:
        is_valid, issues = engine.validate_template_syntax(template_str)
        status = "[OK] Valid" if is_valid else f"[X] Invalid: {issues}"
        print(f"{description}: {status}")
    
    # 9. Usage statistics
    print_section("9. Usage Statistics")
    
    # Access some templates
    engine.get_template("product_description")
    engine.get_template("product_description")
    engine.get_template("social_media_post")
    
    stats = engine.get_usage_stats()
    for name, count in sorted(stats.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {name}: {count} accesses")
    
    # 10. Export templates
    print_section("10. Export Templates")
    exported = engine.export_templates(["product_description", "social_media_post"])
    print(f"Exported {len(exported)} templates")
    for exp in exported:
        print(f"  - {exp['name']} (v{exp['version']})")
    
    print_section("Demo Complete!")
    print("""
What you can do next:
1. Use templates with ContentGenerator for actual AI generation
2. Create custom templates for your specific use cases
3. Implement A/B testing with ab_test_group attribute
4. Export/import templates for sharing across projects
""")


if __name__ == "__main__":
    main()

"""
LaborX Portfolio PDF Generator
Creates a professional PDF portfolio with screenshots for LaborX platform
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from PIL import Image as PILImage
import os
from datetime import datetime

class LaborXPortfolioGenerator:
    """Generate professional PDF portfolio for LaborX"""
    
    def __init__(self, output_filename="AI-ContentGen-Portfolio.pdf"):
        self.output_filename = output_filename
        self.doc = SimpleDocTemplate(
            self.output_filename,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        self.story = []
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#16213e'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#0f3460'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # Highlight box
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1a1a2e'),
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica'
        ))
        
        # Bullet points
        self.styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1a1a2e'),
            leftIndent=30,
            spaceAfter=8,
            fontName='Helvetica',
            bulletIndent=15,
            bulletFontName='Helvetica',
            bulletFontSize=11
        ))
    
    def add_cover_page(self):
        """Add professional cover page"""
        # Title
        title = Paragraph(
            "AI Content Generator Pro",
            self.styles['CustomTitle']
        )
        self.story.append(title)
        self.story.append(Spacer(1, 0.3*inch))
        
        # Subtitle
        subtitle = Paragraph(
            "Professional Full-Stack AI Application",
            self.styles['Subtitle']
        )
        self.story.append(subtitle)
        self.story.append(Spacer(1, 0.5*inch))
        
        # Key stats table
        stats_data = [
            ['Project Type', 'Full-Stack Web Application'],
            ['Technology Stack', 'Python 3.13, Flask, OpenAI API'],
            ['Test Coverage', '95%+ (294 Tests)'],
            ['Lines of Code', '5,000+'],
            ['Documentation', '7 Comprehensive Guides'],
            ['Status', 'Production Ready']
        ]
        
        stats_table = Table(stats_data, colWidths=[2.5*inch, 3.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a2e')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        self.story.append(stats_table)
        self.story.append(Spacer(1, 0.5*inch))
        
        # Description
        desc = Paragraph(
            """
            <b>Project Overview:</b><br/>
            A sophisticated AI-powered content generation platform that leverages OpenAI's GPT models 
            to generate professional content across 10+ templates. Features include a modern web interface, 
            comprehensive REST API, intelligent caching, cost tracking, and extensive testing suite.
            """,
            self.styles['Highlight']
        )
        self.story.append(desc)
        self.story.append(Spacer(1, 0.2*inch))
        
        # Contact info
        contact = Paragraph(
            """
            <b>Developer:</b> Amir Aeiny - Full-Stack Developer<br/>
            <b>GitHub:</b> github.com/DarkOracle10<br/>
            <b>LinkedIn:</b> linkedin.com/in/amir-aeiny-dev
            """,
            self.styles['Highlight']
        )
        self.story.append(contact)
        self.story.append(Spacer(1, 0.3*inch))
        
        # Skills demonstrated
        skills_text = Paragraph(
            "<b>Skills Demonstrated:</b> Backend Development (Python/Flask) • Frontend Development (HTML/CSS/JS) • "
            "API Integration (OpenAI) • Software Architecture • Testing (Pytest) • DevOps (Docker) • "
            "Documentation • UI/UX Design • Error Handling • Performance Optimization",
            self.styles['Highlight']
        )
        self.story.append(skills_text)
        
        self.story.append(PageBreak())
    
    def add_screenshot(self, image_path, caption, max_width=6*inch):
        """Add a screenshot with caption"""
        if os.path.exists(image_path):
            try:
                # Open image to get dimensions
                pil_img = PILImage.open(image_path)
                img_width, img_height = pil_img.size
                
                # Calculate aspect ratio
                aspect = img_height / img_width
                
                # Set image size - make it reasonable for PDF
                target_width = 5.5 * inch  # 5.5 inches wide
                target_height = target_width * aspect
                
                # Limit height to avoid page overflow
                if target_height > 4 * inch:
                    target_height = 4 * inch
                    target_width = target_height / aspect
                
                # Add caption
                caption_para = Paragraph(f"<b>{caption}</b>", self.styles['SectionHeading'])
                self.story.append(caption_para)
                self.story.append(Spacer(1, 0.1*inch))
                
                # Add image
                img = Image(image_path, width=target_width, height=target_height)
                self.story.append(img)
                self.story.append(Spacer(1, 0.2*inch))
                
                print(f"✅ Added screenshot: {os.path.basename(image_path)} ({img_width}x{img_height})")
                return True
            except Exception as e:
                print(f"❌ Error adding screenshot {image_path}: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print(f"❌ Screenshot not found: {image_path}")
            return False
    
    def add_section(self, title, content_list):
        """Add a content section with title and bullet points"""
        # Section title
        heading = Paragraph(title, self.styles['SectionHeading'])
        self.story.append(heading)
        
        # Content
        for item in content_list:
            if item.startswith('•'):
                para = Paragraph(item, self.styles['BulletPoint'])
            else:
                para = Paragraph(item, self.styles['Normal'])
            self.story.append(para)
            self.story.append(Spacer(1, 0.08*inch))
        
        self.story.append(Spacer(1, 0.2*inch))
    
    def add_skills_section(self):
        """Add detailed skills section"""
        self.add_section(
            "💼 Technical Skills Demonstrated",
            [
                "<b>Backend Development:</b>",
                "• Python 3.13 with modern best practices and type hints",
                "• Flask web framework with RESTful API design",
                "• OpenAI API integration with retry logic and error handling",
                "• Session management, rate limiting, and caching strategies",
                "",
                "<b>Frontend Development:</b>",
                "• Responsive HTML5/CSS3 with modern JavaScript (ES6+)",
                "• Dark mode support with persistent user preferences",
                "• Real-time form validation and dynamic content rendering",
                "• Mobile-first design approach with cross-browser compatibility",
                "",
                "<b>Software Architecture:</b>",
                "• Layered architecture (Presentation, Business Logic, Data)",
                "• Design patterns: Factory, Strategy, Facade, Singleton",
                "• Modular component design with separation of concerns",
                "• Scalable architecture ready for microservices migration",
                "",
                "<b>Testing & Quality:</b>",
                "• 294 unit and integration tests with 95%+ code coverage",
                "• Test-driven development (TDD) methodology",
                "• Automated testing with pytest and mock objects",
                "• Continuous integration ready structure"
            ]
        )
    
    def add_features_section(self):
        """Add key features section"""
        self.add_section(
            "🎯 Key Features",
            [
                "<b>Content Generation:</b>",
                "• 10 professional templates (blog posts, product descriptions, social media, etc.)",
                "• Variable-based template system with validation",
                "• Support for GPT-3.5 and GPT-4 models",
                "",
                "<b>Web Interface:</b>",
                "• Clean, intuitive design with dark/light themes",
                "• Real-time generation with progress indicators",
                "• Generation history with export capabilities (JSON/CSV)",
                "• Cost estimation and usage statistics",
                "",
                "<b>API Features:</b>",
                "• 15+ REST endpoints with comprehensive documentation",
                "• Rate limiting and session-based state management",
                "• Health checks and error reporting",
                "• CORS support for cross-origin requests",
                "",
                "<b>Performance:</b>",
                "• Intelligent LRU caching system",
                "• Exponential backoff retry logic",
                "• Optimized database queries and API calls",
                "• Efficient memory management"
            ]
        )
    
    def add_architecture_section(self):
        """Add architecture overview"""
        self.add_section(
            "🏗️ System Architecture",
            [
                "The application follows a clean, layered architecture:",
                "",
                "<b>Client Layer:</b> Web browser, CLI, and API clients",
                "<b>Presentation Layer:</b> Flask routes, templates, and session management",
                "<b>Business Logic Layer:</b> Content generator orchestrator, prompt engine, and API manager",
                "<b>External Services:</b> OpenAI API with retry and error handling",
                "<b>Infrastructure:</b> Configuration management, caching, and logging",
                "",
                "Key architectural patterns:",
                "• Factory Pattern for template creation",
                "• Strategy Pattern for generation strategies",
                "• Facade Pattern for simplified API interface",
                "• Singleton Pattern for configuration management"
            ]
        )
    
    def add_similar_projects(self):
        """Add similar projects section"""
        self.add_section(
            "🚀 Similar Projects I Can Build",
            [
                "<b>Content Management Systems:</b>",
                "• Blog platforms with AI-assisted content creation",
                "• Documentation generators and knowledge bases",
                "• Content scheduling and publishing systems",
                "",
                "<b>API Integration Projects:</b>",
                "• Multi-AI provider platforms (OpenAI, Anthropic, Google)",
                "• Content aggregation and curation systems",
                "• Data processing pipelines with external APIs",
                "",
                "<b>Web Applications:</b>",
                "• E-commerce platforms with product management",
                "• SaaS applications with subscription models",
                "• Admin dashboards and analytics platforms",
                "• Real-time collaboration tools",
                "",
                "<b>AI/ML Applications:</b>",
                "• Chatbot platforms with conversation management",
                "• Sentiment analysis and text classification systems",
                "• Recommendation engines and personalization",
                "• Natural language processing tools"
            ]
        )
    
    def generate(self, screenshot_dir="portfolio_assets"):
        """Generate the complete PDF"""
        print("🎨 Generating LaborX Portfolio PDF...")
        
        # Cover page
        self.add_cover_page()
        
        # Screenshots section
        heading = Paragraph("📸 Application Screenshots", self.styles['CustomTitle'])
        self.story.append(heading)
        self.story.append(Spacer(1, 0.3*inch))
        
        # Try to find screenshots
        screenshots = [
            ("screenshot2.png", "Main Dashboard - Light Mode"),
            ("screenshot4.png", "Main Dashboard - Dark Mode"),
            ("screenshot1.png", "Generation History & Statistics"),
            ("screenshot3.png", "API Documentation Interface")
        ]
        
        for filename, caption in screenshots:
            filepath = os.path.join(screenshot_dir, filename)
            if not os.path.exists(filepath):
                # Try alternative paths
                filepath = f"docs/screenshots/{filename}"
            
            self.add_screenshot(filepath, caption)
        
        self.story.append(PageBreak())
        
        # Content sections
        self.add_skills_section()
        self.story.append(PageBreak())
        
        self.add_features_section()
        self.story.append(Spacer(1, 0.3*inch))
        
        self.add_architecture_section()
        self.story.append(PageBreak())
        
        self.add_similar_projects()
        
        # Footer section
        self.story.append(Spacer(1, 0.5*inch))
        footer = Paragraph(
            f"""
            <b>Why Choose Me?</b><br/>
            ✓ Full-Stack Expertise: Frontend, backend, and deployment<br/>
            ✓ Clean Code: Maintainable, documented, tested (95%+ coverage)<br/>
            ✓ Best Practices: Industry standards and design patterns<br/>
            ✓ Problem Solving: Robust error handling and optimization<br/>
            ✓ Modern Tech: Latest tools and frameworks<br/>
            ✓ Quality Focused: Test-driven development, no shortcuts<br/>
            <br/>
            <b>📞 Contact Information:</b><br/>
            <b>Developer:</b> Amir Aeiny<br/>
            <b>GitHub:</b> github.com/DarkOracle10<br/>
            <b>LinkedIn:</b> linkedin.com/in/amir-aeiny-dev<br/>
            <br/>
            <i>Portfolio Generated: {datetime.now().strftime("%B %d, %Y")}</i><br/>
            <i>Project Status: Production Ready • License: MIT</i>
            """,
            self.styles['Highlight']
        )
        self.story.append(footer)
        
        # Build PDF
        print("📝 Building PDF document...")
        self.doc.build(self.story)
        print(f"✅ Portfolio PDF created: {self.output_filename}")
        
        # Check file size
        file_size = os.path.getsize(self.output_filename) / (1024 * 1024)  # MB
        print(f"📊 File size: {file_size:.2f} MB")
        
        if file_size > 5:
            print("⚠️  WARNING: File size exceeds 5MB limit for LaborX")
            print("   Consider compressing images or splitting into multiple files")
        else:
            print("✅ File size is within LaborX limit (under 5MB)")
        
        return self.output_filename


def main():
    """Main function to generate the portfolio"""
    print("=" * 60)
    print("LaborX Portfolio Generator")
    print("=" * 60)
    
    # Create generator
    generator = LaborXPortfolioGenerator()
    
    # Generate PDF
    output_file = generator.generate()
    
    print("\n" + "=" * 60)
    print(f"Portfolio ready: {output_file}")
    print("=" * 60)
    print("\n📤 Ready to upload to LaborX!")
    print("\nNext steps:")
    print("1. Review the generated PDF")
    print("2. Ensure file size is under 5MB")
    print("3. Upload to LaborX with professional file name")
    print("4. Add project description from LABORX_PORTFOLIO.md")
    

if __name__ == "__main__":
    main()

"""
Copy Screenshots and Regenerate PDF
Helps copy your screenshots and regenerate the portfolio PDF
"""

import os
import shutil
from pathlib import Path

# Paths
screenshots_folder = Path.home() / "Pictures" / "Screenshots"
portfolio_assets = Path("portfolio_assets")
portfolio_assets.mkdir(exist_ok=True)

print("=" * 70)
print("Screenshot Copy Helper for LaborX Portfolio")
print("=" * 70)
print()

# Check for recent screenshots
if screenshots_folder.exists():
    print(f"📁 Found Screenshots folder: {screenshots_folder}")
    
    # Get recent PNG files
    png_files = sorted(screenshots_folder.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if len(png_files) >= 4:
        print(f"\n✅ Found {len(png_files)} screenshots")
        print("\n📋 4 Most recent screenshots:")
        print("-" * 70)
        
        for i, file in enumerate(png_files[:4], 1):
            size_kb = file.stat().st_size / 1024
            mod_time = file.stat().st_mtime
            from datetime import datetime
            date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
            print(f"{i}. {file.name}")
            print(f"   Size: {size_kb:.1f} KB | Modified: {date_str}")
        
        print("\n" + "=" * 70)
        print("📸 Copying screenshots to portfolio_assets...")
        print("=" * 70)
        
        # Copy screenshots with new names
        screenshot_names = [
            ("screenshot1.png", "Dark Mode Dashboard"),
            ("screenshot2.png", "API Documentation"),
            ("screenshot3.png", "Light Mode Dashboard"),
            ("screenshot4.png", "History/Statistics Page")
        ]
        
        copied = 0
        for i, (new_name, description) in enumerate(screenshot_names):
            if i < len(png_files):
                source = png_files[i]
                dest = portfolio_assets / new_name
                
                try:
                    shutil.copy2(source, dest)
                    size_kb = dest.stat().st_size / 1024
                    print(f"✅ Copied: {new_name} ({description}) - {size_kb:.1f} KB")
                    copied += 1
                except Exception as e:
                    print(f"❌ Error copying {new_name}: {e}")
        
        print("\n" + "=" * 70)
        print(f"✅ Successfully copied {copied}/4 screenshots")
        print("=" * 70)
        
        if copied == 4:
            print("\n🎉 All screenshots ready!")
            print("\n📄 Now generating PDF with screenshots...")
            print("=" * 70)
            
            # Import and run the PDF generator
            try:
                import sys
                sys.path.insert(0, os.getcwd())
                from generate_laborx_portfolio import LaborXPortfolioGenerator
                
                generator = LaborXPortfolioGenerator()
                output_file = generator.generate(screenshot_dir="portfolio_assets")
                
                file_size = os.path.getsize(output_file) / (1024 * 1024)
                print(f"\n✅ PDF Generated Successfully!")
                print(f"📄 File: {output_file}")
                print(f"📊 Size: {file_size:.2f} MB")
                
                if file_size < 5:
                    print(f"✅ File size is within LaborX limit (under 5MB)")
                else:
                    print(f"⚠️  Warning: File size exceeds 5MB")
                    print("   Consider compressing screenshots")
                
                print("\n" + "=" * 70)
                print("🎉 Portfolio PDF ready for LaborX upload!")
                print("=" * 70)
                
            except Exception as e:
                print(f"\n❌ Error generating PDF: {e}")
                print("\nManual step: Run 'python generate_laborx_portfolio.py'")
        
    else:
        print(f"\n⚠️  Only found {len(png_files)} screenshots")
        print("Please save all 4 screenshots first")

else:
    print(f"❌ Screenshots folder not found: {screenshots_folder}")
    print("\n📍 Alternative locations to check:")
    print(f"   1. {Path.home() / 'Downloads'}")
    print(f"   2. {Path.home() / 'Desktop'}")
    print(f"   3. {Path.home() / 'OneDrive' / 'Pictures' / 'Screenshots'}")
    print("\nPlease manually copy your 4 screenshots to:")
    print(f"   {portfolio_assets.absolute()}")
    print("\nName them:")
    print("   screenshot1.png - Dark mode dashboard")
    print("   screenshot2.png - API documentation")
    print("   screenshot3.png - Light mode dashboard")
    print("   screenshot4.png - History page")

print("\n" + "=" * 70)

#!/usr/bin/env python3
"""
Frontend test runner for the Home Inventory System.

Runs all frontend tests with proper setup and environment configuration.
Supports both pytest and unittest execution patterns.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Add the frontend directory to Python path
frontend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, frontend_dir)

def run_pytest_tests(test_pattern="test_*.py", verbose=True, coverage=False):
    """Run tests using pytest with enhanced reporting."""
    
    print("🧪 Running Frontend Tests for Home Inventory System (pytest)")
    print("=" * 60)
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=components", "--cov=utils", "--cov-report=term-missing"])
    
    # Add test pattern
    cmd.append(f"tests/{test_pattern}")
    
    # Add output formatting
    cmd.extend(["--tb=short", "--color=yes"])
    
    print(f"Command: {' '.join(cmd)}")
    print("-" * 40)
    
    try:
        # Run pytest
        result = subprocess.run(cmd, cwd=frontend_dir, capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Return success status
        success = result.returncode == 0
        
        if success:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with exit code: {result.returncode}")
        
        return success
        
    except Exception as e:
        print(f"Error running pytest: {e}")
        return False

def run_specific_test_category(category="all", verbose=True):
    """Run specific category of tests."""
    
    test_categories = {
        "error_boundaries": "test_error_boundaries.py",
        "error_handling": "test_error_handling_infrastructure.py", 
        "page_boundaries": "test_page_error_boundaries.py",
        "categories": "test_category_management.py",
        "all": "test_*.py"
    }
    
    if category not in test_categories:
        print(f"❌ Unknown test category: {category}")
        print(f"Available categories: {', '.join(test_categories.keys())}")
        return False
    
    pattern = test_categories[category]
    print(f"🎯 Running {category} tests: {pattern}")
    
    return run_pytest_tests(pattern, verbose)

def run_error_boundary_tests_only():
    """Run only error boundary related tests."""
    
    print("🛡️ Running Error Boundary Tests Only")
    print("=" * 50)
    
    error_boundary_tests = [
        "test_error_boundaries.py",
        "test_error_handling_infrastructure.py",
        "test_page_error_boundaries.py"
    ]
    
    all_passed = True
    
    for test_file in error_boundary_tests:
        print(f"\n🔍 Running {test_file}...")
        print("-" * 30)
        
        success = run_pytest_tests(test_file, verbose=True)
        if not success:
            all_passed = False
            print(f"❌ {test_file} failed")
        else:
            print(f"✅ {test_file} passed")
    
    return all_passed

def check_test_dependencies():
    """Check if required test dependencies are installed."""
    
    required_packages = ["pytest", "streamlit"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Install with: pip install pytest streamlit")
        return False
    
    return True

def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Frontend Test Runner for Home Inventory System")
    parser.add_argument(
        "--category", 
        choices=["all", "error_boundaries", "error_handling", "page_boundaries", "categories"],
        default="all",
        help="Test category to run"
    )
    parser.add_argument(
        "--error-boundaries-only", 
        action="store_true",
        help="Run only error boundary tests"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Include coverage reporting"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="Reduce verbosity"
    )
    
    args = parser.parse_args()
    
    try:
        # Check dependencies
        if not check_test_dependencies():
            sys.exit(1)
        
        print("🏠 Home Inventory System - Frontend Test Suite")
        print("=" * 60)
        
        verbose = not args.quiet
        
        # Run specific test categories
        if args.error_boundaries_only:
            success = run_error_boundary_tests_only()
        else:
            success = run_specific_test_category(args.category, verbose)
        
        if success:
            print("\n🎉 Test execution completed successfully!")
        else:
            print("\n💥 Test execution failed!")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n🚨 Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
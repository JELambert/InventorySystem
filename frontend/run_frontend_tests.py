#!/usr/bin/env python3
"""
Frontend test runner for the Home Inventory System.

Runs all frontend tests with proper setup and environment configuration.
"""

import sys
import os
import unittest
from io import StringIO

# Add the frontend directory to Python path
frontend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, frontend_dir)

def run_frontend_tests():
    """Run all frontend tests and return results."""
    
    print("🧪 Running Frontend Tests for Home Inventory System")
    print("=" * 60)
    
    # Discover and run tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Create a test runner with detailed output
    stream = StringIO()
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=2,
        buffer=True
    )
    
    # Run the tests
    result = runner.run(test_suite)
    
    # Get the output
    test_output = stream.getvalue()
    
    # Print results
    print("\n📋 Test Results:")
    print("-" * 40)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        success = True
    else:
        print("\n❌ Some tests failed!")
        success = False
    
    # Print detailed output
    print("\n📄 Detailed Output:")
    print("-" * 40)
    print(test_output)
    
    # Print failures and errors if any
    if result.failures:
        print("\n💥 FAILURES:")
        print("-" * 40)
        for test, traceback in result.failures:
            print(f"FAIL: {test}")
            print(traceback)
    
    if result.errors:
        print("\n🚨 ERRORS:")
        print("-" * 40)
        for test, traceback in result.errors:
            print(f"ERROR: {test}")
            print(traceback)
    
    return success

def main():
    """Main test runner entry point."""
    try:
        success = run_frontend_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n🚨 Test runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
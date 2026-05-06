#!/usr/bin/env python3
"""
Test runner script for the Navigator Backend application.
Provides easy commands to run different types of tests.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command with description."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0

def main():
    """Main test runner function."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [health|all|coverage|help]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Change to the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if command == "health":
        success = run_command(
            "poetry run python -m pytest tests/test_health_checks.py -v", 
            "Running Health Check Tests"
        )
    elif command == "all":
        success = run_command(
            "poetry run python -m pytest tests/ -v", 
            "Running All Tests"
        )
    elif command == "coverage":
        success = run_command(
            "poetry run python -m pytest tests/ --cov=app --cov-report=html --cov-report=term", 
            "Running Tests with Coverage"
        )
        if success:
            print("\n📊 Coverage report generated in htmlcov/index.html")
    elif command == "help":
        print("\nAvailable commands:")
        print("  health    - Run health check tests only")
        print("  all       - Run all tests")
        print("  coverage  - Run tests with coverage report")
        print("  help      - Show this help message")
        sys.exit(0)
    else:
        print(f"Unknown command: {command}")
        print("Use 'python run_tests.py help' for available commands.")
        sys.exit(1)
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

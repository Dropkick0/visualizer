#!/usr/bin/env python3
"""
Test runner for Portrait Preview Webapp.

Provides easy commands to run different types of tests with proper setup.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def setup_test_environment():
    """Set up the test environment."""
    # Add the project root to Python path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests."""
    cmd = ['python', '-m', 'pytest', 'tests/test_*.py']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=app', '--cov-report=html', '--cov-report=term'])
    
    print("🧪 Running unit tests...")
    return subprocess.run(cmd).returncode


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ['python', '-m', 'pytest', 'tests/test_integration.py']
    
    if verbose:
        cmd.append('-v')
    
    print("🔗 Running integration tests...")
    return subprocess.run(cmd).returncode


def run_all_tests(verbose=False, coverage=False):
    """Run all tests."""
    cmd = ['python', '-m', 'pytest', 'tests/']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=app', '--cov-report=html', '--cov-report=term'])
    
    print("🎯 Running all tests...")
    return subprocess.run(cmd).returncode


def run_specific_test(test_path, verbose=False):
    """Run a specific test file or test function."""
    cmd = ['python', '-m', 'pytest', test_path]
    
    if verbose:
        cmd.append('-v')
    
    print(f"🎯 Running specific test: {test_path}")
    return subprocess.run(cmd).returncode


def check_dependencies():
    """Check if test dependencies are installed."""
    required_packages = [
        'pytest',
        'pytest-cov',
        'pillow',
        'flask',
        'pydantic',
        'loguru',
        'python-magic',
        'opencv-python',
        'psutil'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All test dependencies are installed")
    return True


def generate_test_report():
    """Generate a comprehensive test report."""
    print("📊 Generating comprehensive test report...")
    
    # Run tests with coverage
    cmd = [
        'python', '-m', 'pytest', 'tests/',
        '--cov=app',
        '--cov-report=html:htmlcov',
        '--cov-report=term',
        '--junitxml=test_results.xml',
        '-v'
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ Test report generated successfully!")
        print("📁 HTML coverage report: htmlcov/index.html")
        print("📄 JUnit XML report: test_results.xml")
    
    return result.returncode


def lint_code():
    """Run code linting."""
    print("🔍 Running code linting...")
    
    # Try flake8 first
    try:
        result = subprocess.run(['python', '-m', 'flake8', 'app/', 'tests/'], 
                              capture_output=True)
        if result.returncode == 0:
            print("✅ Code linting passed!")
        else:
            print("❌ Linting issues found:")
            print(result.stdout.decode())
    except FileNotFoundError:
        print("⚠️  flake8 not installed, skipping linting")
    
    return 0


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Test runner for Portrait Preview Webapp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run only unit tests
  python run_tests.py --integration      # Run only integration tests
  python run_tests.py --coverage         # Run with coverage report
  python run_tests.py --check-deps       # Check dependencies
  python run_tests.py --lint             # Run code linting
  python run_tests.py --report           # Generate full report
  python run_tests.py --test tests/test_parse.py::TestFileMakerParser::test_parse_basic_print_line
        """
    )
    
    parser.add_argument('--unit', action='store_true',
                       help='Run only unit tests')
    parser.add_argument('--integration', action='store_true',
                       help='Run only integration tests')
    parser.add_argument('--coverage', action='store_true',
                       help='Generate coverage report')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--check-deps', action='store_true',
                       help='Check if test dependencies are installed')
    parser.add_argument('--lint', action='store_true',
                       help='Run code linting')
    parser.add_argument('--report', action='store_true',
                       help='Generate comprehensive test report')
    parser.add_argument('--test', type=str,
                       help='Run specific test file or function')
    
    args = parser.parse_args()
    
    # Setup test environment
    setup_test_environment()
    
    # Handle specific commands
    if args.check_deps:
        if not check_dependencies():
            return 1
        return 0
    
    if args.lint:
        return lint_code()
    
    if args.report:
        return generate_test_report()
    
    # Check dependencies before running tests
    if not check_dependencies():
        print("\n⚠️  Some dependencies are missing. Tests may fail.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return 1
    
    # Run tests based on arguments
    if args.test:
        return run_specific_test(args.test, args.verbose)
    elif args.unit:
        return run_unit_tests(args.verbose, args.coverage)
    elif args.integration:
        return run_integration_tests(args.verbose)
    else:
        return run_all_tests(args.verbose, args.coverage)


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code) 
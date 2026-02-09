#!/usr/bin/env python3
"""Verification script to check all quality standards."""

import subprocess
import sys

def run_check(name, command):
    """Run a quality check and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        print(f"Exit code: {result.returncode}")

        if result.stdout:
            print(f"Output:\n{result.stdout}")

        if result.stderr:
            print(f"Errors:\n{result.stderr}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all quality checks."""
    print("=" * 60)
    print("QUALITY ASSURANCE VERIFICATION")
    print("=" * 60)

    checks = [
        ("Black Formatting", "python3 -m black --check src/ tests/"),
        ("Ruff Linting", "python3 -m ruff check src/advanced_prep tests/advanced_prep"),
        ("MyPy Type Checking", "python3 -m mypy src/advanced_prep --ignore-missing-imports"),
        ("Pytest Tests", "python3 -m pytest tests/advanced_prep/ -q"),
    ]

    results = {}

    for name, command in checks:
        results[name] = run_check(name, command)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - PRODUCTION READY")
    else:
        print("⚠️  SOME CHECKS FAILED - REVIEW NEEDED")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Test runner for the backend multimodal LLM services.
Run this from the backend directory to execute all tests.
"""
import subprocess
import sys
import os
from pathlib import Path


def run_test(test_file):
    """Run a single test file and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=Path(__file__).parent,  # Run from tests directory
            capture_output=False,
            check=True,
        )
        print(f"✅ {test_file} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {test_file} - FAILED (exit code: {e.returncode})")
        return False
    except Exception as e:
        print(f"❌ {test_file} - ERROR: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 Running Backend Tests")
    print("=" * 60)

    # List of test files to run
    test_files = [
        "test_pipeline_changes.py",  # Quick verification test first
        "test_stt.py",
        "test_tts.py",
        "test_multimodal.py",
        "test_speech_sessions.py",
        "test_pipeline.py",  # Full integration test last
    ]

    # Check if we're in the tests directory
    tests_dir = Path(__file__).parent
    if not tests_dir.name == "tests":
        print("❌ Script must be run from the tests directory!")
        return 1

    # Run each test
    passed = 0
    failed = 0

    for test_file in test_files:
        test_path = tests_dir / test_file
        if test_path.exists():
            if run_test(test_file):
                passed += 1
            else:
                failed += 1
        else:
            print(f"⚠️  Test file not found: {test_file}")
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Results Summary")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")

    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n💥 {failed} test(s) failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

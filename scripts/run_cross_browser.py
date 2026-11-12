"""Cross-browser test runner for TC-Compat-01.

Runs the Playwright E2E test suite across Chromium, Firefox, and WebKit,
collects execution results, and produces a summary validation table.

Usage:
    python scripts/run_cross_browser.py
    python scripts/run_cross_browser.py --browsers chromium,firefox
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_BROWSERS = ("chromium", "firefox", "webkit")


def run_browser_suite(browser: str, verbose: bool = False) -> dict:
    env = {**os.environ, "PLAYWRIGHT_BROWSER": browser}
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/e2e/test_canvas_sync.py",
        "-v" if verbose else "-q",
    ]

    print(f"[*] Running E2E suite on {browser.capitalize()}...")
    start_time = time.time()
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    duration = time.time() - start_time

    output = proc.stdout + proc.stderr
    passed = 0
    failed = 0
    skipped = 0

    # Parse counts from pytest summary line (e.g., "15 passed in 18.38s")
    for line in output.splitlines():
        if "passed" in line or "failed" in line or "skipped" in line:
            parts = line.strip("= ").split(",")
            for p in parts:
                p = p.strip()
                if "passed" in p:
                    try:
                        passed = int(p.split()[0])
                    except (ValueError, IndexError):
                        pass
                elif "failed" in p:
                    try:
                        failed = int(p.split()[0])
                    except (ValueError, IndexError):
                        pass
                elif "skipped" in p:
                    try:
                        skipped = int(p.split()[0])
                    except (ValueError, IndexError):
                        pass

    success = (proc.returncode == 0) and (failed == 0) and (passed > 0)
    return {
        "browser": browser,
        "success": success,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": passed + failed + skipped,
        "duration": duration,
        "output": output,
    }


def main():
    parser = argparse.ArgumentParser(description="Run E2E tests across browsers (TC-Compat-01)")
    parser.add_argument(
        "--browsers",
        default="chromium,firefox,webkit",
        help="Comma-separated list of browsers (chromium, firefox, webkit)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose pytest output")
    args = parser.parse_args()

    targets = [b.strip().lower() for b in args.browsers.split(",") if b.strip()]
    for b in targets:
        if b not in SUPPORTED_BROWSERS:
            print(f"Error: Unsupported browser '{b}'. Supported: {', '.join(SUPPORTED_BROWSERS)}")
            sys.exit(1)

    print("=" * 65)
    print(" TC-Compat-01 Cross-Browser Verification Suite")
    print(f" Browsers: {', '.join(targets)}")
    print("=" * 65)

    results = []
    all_ok = True

    for browser in targets:
        res = run_browser_suite(browser, verbose=args.verbose)
        results.append(res)
        if not res["success"]:
            all_ok = False
        status_str = "PASS" if res["success"] else "FAIL"
        print(f"    -> {browser.capitalize()}: {status_str} ({res['passed']}/{res['total']} passed in {res['duration']:.2f}s)")

    print("\n" + "=" * 65)
    print(" Execution Summary (TC-Compat-01)")
    print("=" * 65)
    print(f"{'Browser':<12} | {'Total':<6} | {'Passed':<6} | {'Failed':<6} | {'Time (s)':<8} | {'Status':<6}")
    print("-" * 65)

    total_exec = 0
    total_passed = 0
    total_failed = 0
    total_time = 0.0

    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        print(f"{r['browser'].capitalize():<12} | {r['total']:<6} | {r['passed']:<6} | {r['failed']:<6} | {r['duration']:<8.2f} | {status:<6}")
        total_exec += r["total"]
        total_passed += r["passed"]
        total_failed += r["failed"]
        total_time += r["duration"]

    print("-" * 65)
    print(f"{'Total':<12} | {total_exec:<6} | {total_passed:<6} | {total_failed:<6} | {total_time:<8.2f} | {'ALL PASS' if all_ok else 'FAILED'}")
    print("=" * 65)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()

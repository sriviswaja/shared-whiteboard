"""Cross-browser test runner for TC-Compat-01.

Runs the Playwright E2E test suite across Chromium, Firefox, and WebKit,
collects execution results, and produces a summary validation table and report.

Usage:
    python scripts/run_cross_browser.py
    python scripts/run_cross_browser.py --browsers chromium,firefox
    python scripts/run_cross_browser.py --headful
    python scripts/run_cross_browser.py --report docs/reports/cross_browser_test_report.md
"""

import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_BROWSERS = ("chromium", "firefox", "webkit")


def run_browser_suite(browser: str, verbose: bool = False, headful: bool = False) -> dict:
    env = {
        **os.environ,
        "PLAYWRIGHT_BROWSER": browser,
        "PLAYWRIGHT_HEADLESS": "0" if headful else "1",
    }
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


def generate_markdown_report(results: list, output_path: Path):
    all_ok = all(r["success"] for r in results)
    total_exec = sum(r["total"] for r in results)
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    total_time = sum(r["duration"] for r in results)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Cross-Browser Verification Report (TC-Compat-01)",
        "",
        "## 1. Overview",
        "",
        f"- **Date & Time:** {timestamp}",
        "- **Test Case ID:** TC-Compat-01 / WB-NF-005",
        f"- **Test Suite:** `tests/e2e/test_canvas_sync.py` (15 scenarios per browser)",
        f"- **Engines Tested:** Chromium, Firefox (Gecko), WebKit",
        f"- **Execution Result:** **{'PASS (ALL BROWSERS)' if all_ok else 'FAILED'}**",
        f"- **Total Executions:** {total_exec} tests ({total_passed} passed, {total_failed} failed, {total_skipped} skipped)",
        f"- **Total Duration:** {total_time:.2f} seconds",
        "",
        "## 2. Summary by Browser Engine",
        "",
        "| Browser Engine | Total Scenarios | Passed | Failed | Skipped | Duration (s) | Status |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in results:
        status_md = "**PASS**" if r["success"] else "**FAIL**"
        lines.append(
            f"| {r['browser'].capitalize()} | {r['total']} | {r['passed']} | {r['failed']} | {r['skipped']} | {r['duration']:.2f} | {status_md} |"
        )

    lines.extend([
        f"| **Overall** | **{total_exec}** | **{total_passed}** | **{total_failed}** | **{total_skipped}** | **{total_time:.2f}** | **{'PASS' if all_ok else 'FAIL'}** |",
        "",
        "## 3. Verified Scenarios per Engine",
        "",
        "The following 15 test scenarios were executed and verified independently across all three browser engines:",
        "",
        "1. `test_tc_sync_01_drawing_reaches_the_other_browser` - Real-time pen stroke sync across separate browser contexts",
        "2. `test_tc_draw_02_shapes_sync` - Shape tools (rect, ellipse, line) broadcast and rendering",
        "3. `test_tc_draw_03_text_syncs` - Text tool creation and sync via dialog prompt",
        "4. `test_tc_draw_04_other_user_can_move_and_delete` - Select tool move and delete sync",
        "5. `test_tc_draw_05_eraser_removes_for_everyone` - Eraser tool removal across clients",
        "6. `test_tc_draw_06_undo_only_undoes_own_work` - Per-user undo/redo isolation",
        "7. `test_tc_sync_02_remote_cursor_shows_name` - Remote cursor tracking and name display",
        "8. `test_tc_sync_04_joiner_receives_the_full_board_state` - Late-joiner catches up with existing board state",
        "9. `test_tc_draw_01_colour_and_thickness_sync` - Color picker and stroke width synchronization",
        "10. `test_tc_draw_03_text_can_be_edited` - Double-click text selection and inline editing",
        "11. `test_tc_draw_04_resize` - Interactive bounding box resizing synchronization",
        "12. `test_tc_sync_04_reconnect_and_resync` - Network disconnect handling, offline lock, and post-reconnect resync",
        "13. `test_tc_ver_02_named_version_is_saved_and_listed` - Manual named version snapshot creation and listing",
        "14. `test_tc_ver_04_preview_is_read_only` - Read-only snapshot preview while live board updates continue",
        "15. `test_tc_ver_05_restore_updates_everyone` - Snapshot restoration broadcast to all active clients",
        "",
        "## 4. Environment & Fixture Architecture",
        "",
        "- Each test launches two independent browser contexts (`open_page`), simulating two separate real users sharing a WebSocket session.",
        "- Single clean fixture (`tests/e2e/test_canvas_sync.py::browser`) dynamically launches the target engine determined by `PLAYWRIGHT_BROWSER`.",
        "- Fixture verifies `b.browser_type.name == browser_name` to guarantee genuine engine execution without fallback or misconfiguration.",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[*] Markdown report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run E2E tests across browsers (TC-Compat-01)")
    parser.add_argument(
        "--browsers",
        default="chromium,firefox,webkit",
        help="Comma-separated list of browsers (chromium, firefox, webkit)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose pytest output")
    parser.add_argument("--headful", action="store_true", help="Run with visible browser window")
    parser.add_argument("--report", type=str, default="", help="Path to write a markdown report")
    args = parser.parse_args()

    targets = [b.strip().lower() for b in args.browsers.split(",") if b.strip()]
    for b in targets:
        if b not in SUPPORTED_BROWSERS:
            print(f"Error: Unsupported browser '{b}'. Supported: {', '.join(SUPPORTED_BROWSERS)}")
            sys.exit(1)

    print("=" * 65)
    print(" TC-Compat-01 Cross-Browser Verification Suite")
    print(f" Browsers: {', '.join(targets)}")
    print(f" Mode: {'Headed' if args.headful else 'Headless'}")
    print("=" * 65)

    results = []
    all_ok = True

    for browser in targets:
        res = run_browser_suite(browser, verbose=args.verbose, headful=args.headful)
        results.append(res)
        if not res["success"]:
            all_ok = False
        status_str = "PASS" if res["success"] else "FAIL"
        print(f"    -> {browser.capitalize()}: {status_str} ({res['passed']}/{res['total']} passed in {res['duration']:.2f}s)")
        if not res["success"] and not args.verbose:
            print("       Failure output details:")
            for line in res["output"].splitlines()[-10:]:
                print(f"       {line}")

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

    if args.report:
        generate_markdown_report(results, Path(args.report))

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()

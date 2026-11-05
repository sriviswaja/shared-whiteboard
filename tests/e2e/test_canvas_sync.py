"""Browser tests: two real browsers share one board through the server (WebSocket).

Skipped automatically when Playwright or its browsers are not installed, so the normal
CI run (pip install -r requirements.txt) is unaffected. To run them locally:

    pip install playwright && playwright install chromium
    pytest tests/e2e -v
"""
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    db = tmp_path_factory.mktemp("e2e") / "e2e.db"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.server.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env={**__import__("os").environ, "DATABASE_URL": f"sqlite:///{db}"})
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(base + "/healthz").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("server did not start")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:   # browsers not installed
            pytest.skip(f"chromium not available: {exc}")
        yield b
        b.close()


@pytest.fixture()
def board(server):
    return server, httpx.post(server + "/api/boards", json={"name": "e2e"}).json()["id"]


def open_page(browser, base, board_id, name):
    page = browser.new_context().new_page()   # separate context: no shared tab storage
    page.reply = ["Hello"]                    # what prompt() boxes get answered with
    page.on("dialog", lambda d: d.accept(page.reply[0]))
    page.goto(f"{base}/?board={board_id}&name={name}")
    page.wait_for_function("Sync.online === true")
    return page


def drag(page, x1, y1, x2, y2):
    box = page.locator("#board").bounding_box()
    page.mouse.move(box["x"] + x1, box["y"] + y1)
    page.mouse.down()
    page.mouse.move(box["x"] + (x1 + x2) / 2, box["y"] + (y1 + y2) / 2)
    page.mouse.move(box["x"] + x2, box["y"] + y2)
    page.mouse.up()


def count(page):
    return page.evaluate("objs.length")


def test_tc_sync_01_drawing_reaches_the_other_browser(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    drag(a, 50, 50, 200, 120)                                  # pen
    b.wait_for_function("objs.length === 1")
    assert b.evaluate("objs[0].type") == "pen"
    assert b.evaluate("objs[0].pts.length") >= 2


def test_tc_draw_02_shapes_sync(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    for tool, box in (("rect", (40, 40, 140, 100)), ("ellipse", (160, 40, 260, 100)), ("line", (40, 150, 260, 190))):
        a.click(f"#tool-{tool}")
        drag(a, *box)
    b.wait_for_function("objs.length === 3")
    assert b.evaluate("objs.map(o => o.type)") == ["rect", "ellipse", "line"]


def test_tc_draw_03_text_syncs(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    a.click("#tool-text")
    box = a.locator("#board").bounding_box()
    a.mouse.click(box["x"] + 80, box["y"] + 80)
    b.wait_for_function("objs.length === 1")
    assert b.evaluate("objs[0].text") == "Hello"


def test_tc_draw_04_other_user_can_move_and_delete(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    a.click("#tool-rect")
    drag(a, 100, 100, 200, 180)
    b.wait_for_function("objs.length === 1")
    b.click("#tool-select")
    drag(b, 150, 100, 250, 160)                                # grab the top edge and drag it
    a.wait_for_function("objs[0].x > 150")                     # the move reached A
    b.click("#btn-delete")
    a.wait_for_function("objs.length === 0")


def test_tc_draw_05_eraser_removes_for_everyone(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    a.click("#tool-rect")
    drag(a, 100, 100, 200, 180)
    b.wait_for_function("objs.length === 1")
    b.click("#tool-eraser")
    drag(b, 100, 100, 110, 110)
    a.wait_for_function("objs.length === 0")


def test_tc_draw_06_undo_only_undoes_own_work(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    drag(a, 50, 50, 150, 90)                                   # S1 by A
    b.wait_for_function("objs.length === 1")
    drag(b, 50, 200, 150, 240)                                 # S2 by B
    a.wait_for_function("objs.length === 2")
    a.click("#btn-undo")                                       # A undoes S1, B's S2 must stay
    b.wait_for_function("objs.length === 1")
    assert a.evaluate("objs.length") == 1
    a.click("#btn-redo")
    b.wait_for_function("objs.length === 2")


def test_tc_sync_02_remote_cursor_shows_name(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    box = a.locator("#board").bounding_box()
    for i in range(5):
        a.mouse.move(box["x"] + 100 + i * 10, box["y"] + 100)
        a.wait_for_timeout(80)
    b.wait_for_selector(".cursor")
    assert b.locator(".cursor").first.inner_text() == "Alice"


def test_tc_board_02_late_joiner_gets_existing_drawing(browser, board):
    base, bid = board
    a = open_page(browser, base, bid, "Alice")
    drag(a, 50, 50, 200, 120)
    a.wait_for_timeout(300)
    c = open_page(browser, base, bid, "Carol")
    assert count(c) == 1


def test_tc_draw_01_colour_and_thickness_sync(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    a.fill("#color", "#ff0000")
    a.select_option("#width", "5")
    drag(a, 50, 50, 200, 90)
    a.fill("#color", "#0000ff")
    a.select_option("#width", "2")
    drag(a, 50, 150, 200, 190)
    b.wait_for_function("objs.length === 2")
    assert b.evaluate("objs.map(o => [o.color, o.width])") == [["#ff0000", 5], ["#0000ff", 2]]


def test_tc_draw_03_text_can_be_edited(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    a.click("#tool-text")
    box = a.locator("#board").bounding_box()
    a.mouse.click(box["x"] + 80, box["y"] + 80)
    b.wait_for_function("objs.length === 1")
    a.reply[0] = "Hi"
    a.click("#tool-select")
    a.mouse.dblclick(box["x"] + 85, box["y"] + 75)
    b.wait_for_function("objs[0].text === 'Hi'")


def test_tc_draw_04_resize(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    a.click("#tool-rect")
    drag(a, 100, 100, 200, 160)
    b.wait_for_function("objs.length === 1")
    b.click("#tool-select")
    drag(b, 150, 100, 150, 100)                                # click the rectangle to select it
    box = b.locator("#board").bounding_box()
    b.mouse.move(box["x"] + 204, box["y"] + 164)               # the resize handle (bottom-right)
    b.mouse.down()
    b.mouse.move(box["x"] + 280, box["y"] + 230)
    b.mouse.up()
    a.wait_for_function("objs[0].w > 150")


def test_tc_sync_04_reconnect_and_resync(browser, board):
    base, bid = board
    a = open_page(browser, base, bid, "Alice")
    ctx = browser.new_context()
    b = ctx.new_page()
    net = {"down": False, "sockets": []}

    def gateway(ws):                                           # sits between B and the server
        if net["down"]:
            ws.close()
            return
        ws.connect_to_server()
        net["sockets"].append(ws)

    ctx.route_web_socket("**/ws/boards/**", gateway)
    b.goto(f"{base}/?board={bid}&name=Bob")
    b.wait_for_function("Sync.online === true")
    net["down"] = True                                         # B loses the network
    for ws in net["sockets"]:
        ws.close()
    b.wait_for_function("Sync.online === false")
    drag(a, 50, 50, 200, 120)                                  # A keeps drawing meanwhile
    drag(b, 50, 200, 200, 240)                                 # B cannot draw while offline
    assert count(b) == 0
    net["down"] = False                                        # network comes back
    b.wait_for_function("Sync.online === true && objs.length === 1", timeout=30000)


def test_tc_ver_save_preview_restore_from_the_ui(browser, board):
    base, bid = board
    a, b = open_page(browser, base, bid, "Alice"), open_page(browser, base, bid, "Bob")
    drag(a, 50, 50, 200, 90)                                   # one stroke
    b.wait_for_function("objs.length === 1")
    a.reply[0] = "first draft"
    a.click("#btn-save")                                       # TC-Ver-01: manual named version
    a.wait_for_function("document.getElementById('status').textContent === 'Version saved'")
    drag(a, 50, 150, 200, 190)                                 # a second stroke, after the version
    b.wait_for_function("objs.length === 2")

    a.click("#btn-versions")
    a.wait_for_selector("#versions .ver")
    assert "first draft" in a.locator("#versions .ver").first.inner_text()
    a.locator("#versions .ver button", has_text="Preview").first.click()   # TC-Ver-02: read-only preview
    a.wait_for_function("previewObjs !== null && previewObjs.length === 1")
    assert a.evaluate("objs.length") == 2                      # live board untouched
    drag(a, 60, 300, 200, 330)                                 # drawing is ignored while previewing
    assert a.evaluate("objs.length") == 2
    a.click("#banner button")                                  # back to live

    a.locator("#versions .ver button", has_text="Restore").first.click()   # TC-Ver-03: restore
    a.wait_for_function("objs.length === 1")
    b.wait_for_function("objs.length === 1")                   # Bob sees it without reloading

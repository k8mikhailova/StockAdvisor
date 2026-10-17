"""
End-to-end browser checks for the onboarding tour (desktop spotlight and narrow-screen walkthrough).
Run with:  pip install -r requirements.txt pytest playwright  &&  playwright install chromium  &&  python -m pytest tests
These tests are skipped when Playwright or its browser is not installed.
"""
import os
import socket
import subprocess
import sys
import time

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = {"width": 1400, "height": 900}
PHONE = {"width": 390, "height": 844}
WELCOME = "Want a quick walkthrough?"

HIGHLIGHT_BOX = """() => { const a = document.querySelector('.driver-active-element');
  if (!a) return null; const r = a.getBoundingClientRect();
  return {left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height,
          vw: window.innerWidth, vh: window.innerHeight}; }"""


@pytest.fixture(scope="module")
def app_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {k: v for k, v in os.environ.items() if k not in ("FMP_API_KEY", "EMAIL_ADDRESS", "EMAIL_PASSWORD",
                                                            "STOCKADVISOR_MODE")}
    server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "main.py", "--server.headless", "true",
                               "--server.port", str(port), "--browser.gatherUsageStats", "false"],
                              cwd=APP_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = f"http://localhost:{port}"
    for _ in range(60):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            break
        except OSError:
            time.sleep(1)
    yield url
    server.terminate()
    output = server.communicate(timeout=30)[0]
    assert "Traceback" not in output, output


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:
            pytest.skip(f"Chromium for Playwright is not installed: {e}")
        yield b
        b.close()


class Visitor:
    """A fresh browser context (new localStorage) that records errors and blocks external requests."""

    def __init__(self, browser, url, viewport, block_tour_component=False):
        mobile = viewport["width"] < 768
        self.context = browser.new_context(viewport=viewport, is_mobile=mobile, has_touch=mobile)
        self.external_requests = []
        self.page_errors = []

        def route(r):
            if not r.request.url.startswith(url) and not r.request.url.startswith("data:"):
                self.external_requests.append(r.request.url)
                return r.abort()
            if block_tour_component and "streamlit_tour" in r.request.url and r.request.url.endswith(".js"):
                return r.abort()
            return r.continue_()

        self.context.route("**/*", route)
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda e: self.page_errors.append(str(e)))
        self.url = url
        self.open()

    def open(self):
        self.page.goto(self.url, wait_until="networkidle")
        self.page.get_by_text("Demo mode.").wait_for(timeout=60000)
        self.page.wait_for_timeout(2500)  # let the tour helper report the viewport

    def button(self, name):
        return self.page.get_by_role("button", name=name, exact=True)

    def popover_progress(self):
        popover = self.page.locator(".driver-popover")
        popover.wait_for(timeout=20000)
        self.page.wait_for_timeout(900)  # let Driver.js finish moving the highlight
        return self.page.locator(".driver-popover-progress-text").inner_text()

    def assert_clean(self):
        p = self.page
        assert p.locator('[data-testid="stException"]').count() == 0
        assert not self.external_requests, self.external_requests
        assert not self.page_errors, self.page_errors

    def close(self):
        self.context.close()


@pytest.fixture
def visitor(browser, app_url):
    created = []

    def make(viewport=DESKTOP, **kwargs):
        v = Visitor(browser, app_url, viewport, **kwargs)
        created.append(v)
        return v

    yield make
    for v in created:
        v.close()


def assert_highlight_on_screen(page, in_sidebar=True):
    box = page.evaluate(HIGHLIGHT_BOX)
    assert box and box["width"] > 0 and box["height"] > 0
    assert 0 <= box["left"] and box["right"] <= box["vw"] and box["top"] < box["vh"] and box["bottom"] > 0
    sidebar_right = page.locator('[data-testid="stSidebar"]').bounding_box()
    if in_sidebar:
        assert box["right"] <= sidebar_right["x"] + sidebar_right["width"] + 1


def test_desktop_spotlight_tour(visitor):
    v = visitor()
    p = v.page
    assert p.get_by_text(WELCOME).is_visible()
    assert v.button("Run Simulation").is_enabled()  # the app is usable while the welcome card is shown

    v.button("Start tour").click()
    assert v.popover_progress() == "1 of 5"
    assert p.locator(".driver-popover-title").inner_text() == "Choose your stocks"
    assert_highlight_on_screen(p)
    assert p.locator(".driver-popover-prev-btn").inner_text() == "Back"

    p.locator(".driver-popover-next-btn").click()
    assert v.popover_progress() == "2 of 5"
    assert_highlight_on_screen(p)
    p.locator(".driver-popover-prev-btn").click()
    assert v.popover_progress() == "1 of 5"

    for expected in ["2 of 5", "3 of 5", "4 of 5", "5 of 5"]:
        p.locator(".driver-popover-next-btn").click()
        assert v.popover_progress() == expected
    assert p.locator(".driver-popover-next-btn").inner_text() == "Done"
    p.locator(".driver-popover-next-btn").click()
    p.locator(".driver-popover").wait_for(state="detached", timeout=10000)

    # the tour never runs a simulation
    p.wait_for_timeout(1000)
    assert p.locator(".js-plotly-plot").count() == 0

    # the welcome card does not come back after a refresh, but the tour can be replayed
    v.open()
    assert p.get_by_text(WELCOME).count() == 0
    assert v.button("Take a tour").is_visible()
    v.assert_clean()


def test_tour_can_be_dismissed_any_time(visitor):
    v = visitor()
    p = v.page
    v.button("No thanks").click()
    p.get_by_text(WELCOME).wait_for(state="detached", timeout=10000)

    v.button("Take a tour").click()
    v.popover_progress()
    p.keyboard.press("Escape")
    p.locator(".driver-popover").wait_for(state="detached", timeout=10000)

    v.button("Take a tour").click()
    v.popover_progress()
    p.locator(".driver-popover-close-btn").click()
    p.locator(".driver-popover").wait_for(state="detached", timeout=10000)

    v.open()
    assert p.get_by_text(WELCOME).count() == 0
    v.assert_clean()


def test_results_step_highlights_results(visitor):
    v = visitor()
    p = v.page
    v.button("No thanks").click()
    v.button("Run Simulation").click()
    p.get_by_text("Period: 26 Weeks (ending 2024-09-05)").wait_for(timeout=120000)

    v.button("Take a tour").click()
    v.popover_progress()
    for expected in ["2 of 5", "3 of 5", "4 of 5"]:
        p.locator(".driver-popover-next-btn").click()
        assert v.popover_progress() == expected
    assert p.locator(".driver-popover-title").inner_text() == "Explore the results"
    box = p.evaluate(HIGHLIGHT_BOX)
    assert box and box["left"] > p.locator('[data-testid="stSidebar"]').bounding_box()["width"]
    p.keyboard.press("Escape")
    assert p.locator(".js-plotly-plot").count() == 4  # results are unchanged by the tour
    v.assert_clean()


def run_walkthrough(v):
    p = v.page
    dialog = p.get_by_role("dialog")
    dialog.wait_for(timeout=20000)
    p.wait_for_timeout(500)
    assert p.locator(".driver-popover").count() == 0
    assert p.locator(".driver-active-element").count() == 0
    assert "1 of 5" in dialog.inner_text() and "Choose your stocks" in dialog.inner_text()

    dialog.get_by_role("button", name="Next").click()
    p.get_by_text("2 of 5").wait_for(timeout=10000)
    dialog.get_by_role("button", name="Back").click()
    p.get_by_text("1 of 5").wait_for(timeout=10000)
    for n in range(2, 6):
        dialog.get_by_role("button", name="Next").click()
        p.get_by_text(f"{n} of 5").wait_for(timeout=10000)
    dialog.get_by_role("button", name="Done").click()
    dialog.wait_for(state="detached", timeout=10000)
    assert p.locator(".driver-active-element").count() == 0


def test_narrow_viewport_uses_walkthrough(visitor):
    v = visitor(PHONE)
    p = v.page
    assert p.get_by_text(WELCOME).is_visible()
    v.button("Start tour").click()
    assert "Tap » at the top left" in p.get_by_role("dialog").inner_text()
    run_walkthrough(v)
    assert p.locator(".js-plotly-plot").count() == 0

    # skip from the middle of the walkthrough
    v.button("Take a tour").click()
    dialog = p.get_by_role("dialog")
    dialog.get_by_role("button", name="Next").click()
    p.get_by_text("2 of 5").wait_for(timeout=10000)
    dialog.get_by_role("button", name="Skip").click()
    dialog.wait_for(state="detached", timeout=10000)

    v.open()
    assert p.get_by_text(WELCOME).count() == 0
    v.assert_clean()


def test_collapsed_sidebar_on_desktop_uses_walkthrough(visitor):
    v = visitor()
    p = v.page
    v.button("No thanks").click()
    p.get_by_test_id("stSidebar").hover()
    p.get_by_test_id("stSidebarCollapseButton").locator("button").click()
    p.wait_for_timeout(2000)
    v.button("Take a tour").click()
    run_walkthrough(v)
    v.assert_clean()


def test_shrinking_window_mid_tour_never_highlights_hidden_controls(visitor):
    v = visitor()
    p = v.page
    v.button("Start tour").click()
    v.popover_progress()
    p.locator(".driver-popover-next-btn").click()
    assert v.popover_progress() == "2 of 5"

    p.set_viewport_size(PHONE)
    dialog = p.get_by_role("dialog")
    dialog.wait_for(timeout=20000)
    assert "Compare strategies" in dialog.inner_text()  # continues at the same step
    p.wait_for_timeout(1000)
    assert p.locator(".driver-popover").count() == 0
    assert p.locator(".driver-active-element").count() == 0
    v.assert_clean()


def test_app_works_when_tour_component_fails_to_load(visitor):
    v = visitor(block_tour_component=True)
    p = v.page
    v.button("Start tour").click()
    p.wait_for_timeout(2000)
    v.button("Run Simulation").click()
    p.get_by_text("Period: 26 Weeks (ending 2024-09-05)").wait_for(timeout=120000)
    p.wait_for_timeout(2000)
    assert p.locator(".js-plotly-plot").count() == 4
    assert p.locator('[data-testid="stException"]').count() == 0
    assert not v.external_requests

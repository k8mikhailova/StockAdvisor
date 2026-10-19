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
WELCOME = "A quick tour (about a minute)"
WELCOME_TITLE = "Welcome to StockAdvisor"

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
        self.page.get_by_text("Your portfolio").wait_for(timeout=60000)
        self.page.wait_for_timeout(2500)  # let the tour helper report the viewport

    def button(self, name):
        if name == "Take a tour":
            # the main-area link (the sidebar has one too, which is off-screen on phones)
            return self.page.locator(".st-key-tour_replay_main").get_by_role("button", name=name)
        return self.page.get_by_role("button", name=name, exact=True).filter(visible=True).first

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


TITLES = ["Two pages", "Set up the portfolio", "Choose stocks and data", "Pick what to test", "Compare strategies",
          "Check and run", "You're all set!"]
TITLES_WITH_RESULTS = TITLES[:-1] + ["Read the results"] + TITLES[-1:]
# highlighted container and whether it is in the sidebar, for every step except the finish card
TARGETS = [("st-key-tour_pages", True), ("st-key-tour_portfolio", True), ("st-key-tour_inputs", True),
           ("st-key-tour_simulation", True), ("st-key-tour_advisors", True), ("st-key-tour_run", False)]
RESULTS_TITLE = "Simulation results"

SIDEBAR_INPUTS = """() => [...document.querySelectorAll('[data-testid="stSidebar"] input')]
  .map(e => e.type === 'checkbox' ? e.checked : e.value)"""


def assert_highlight_on_screen(page, in_sidebar=True):
    box = page.evaluate(HIGHLIGHT_BOX)
    assert box and box["width"] > 0 and box["height"] > 0
    assert 0 <= box["left"] and box["right"] <= box["vw"] and box["top"] < box["vh"] and box["bottom"] > 0
    sidebar_right = page.locator('[data-testid="stSidebar"]').bounding_box()
    if in_sidebar:
        assert box["right"] <= sidebar_right["x"] + sidebar_right["width"] + 1


def highlighted_key(page):
    return page.evaluate("""() => { const a = document.querySelector('.driver-active-element');
      return a ? [...a.classList].find(c => c.startsWith('st-key-')) : null; }""")


def wait_for_welcome(page, seconds=15, frame=None):
    """The welcome dialog a first-time visitor sees without clicking anything, or None."""
    root = frame or page
    dialog = root.get_by_role("dialog").filter(has_text=WELCOME_TITLE)
    for _ in range(seconds * 4):
        if dialog.count() and dialog.is_visible():
            return dialog
        page.wait_for_timeout(250)
    return None


def skip_welcome(v):
    assert wait_for_welcome(v.page) is not None
    v.button("Skip for now").click()
    v.page.get_by_text(WELCOME).wait_for(state="detached", timeout=10000)
    v.page.get_by_role("dialog").wait_for(state="detached", timeout=10000)  # let the dialog finish closing
    v.page.wait_for_timeout(500)
    # the choice is stored at once, so even an immediate refresh keeps it
    assert v.page.evaluate("() => window.localStorage.getItem('stockadvisor-tour-seen')") == "1"


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_first_visit_sees_welcome_automatically(visitor, viewport):
    """A brand-new browser (empty localStorage, like Incognito) gets the welcome without any clicks."""
    v = visitor(viewport)
    p = v.page
    assert p.evaluate("() => window.localStorage.length") == 0
    welcome = wait_for_welcome(p)
    assert welcome is not None
    text = welcome.inner_text()
    assert "about a minute" in text and "Take a tour" in text
    assert welcome.get_by_role("button", name="Start the tour").is_visible()
    assert welcome.get_by_role("button", name="Skip for now").is_visible()
    assert p.locator(".js-plotly-plot").count() == 0  # nothing ran

    welcome.get_by_role("button", name="Start the tour").click()
    if viewport is DESKTOP:
        # the spotlight tour, starting at the first sidebar control
        assert v.popover_progress() == f"1 of {len(TITLES)}"
        assert highlighted_key(p) == TARGETS[0][0]
        p.keyboard.press("Escape")
        p.locator(".driver-popover").wait_for(state="detached", timeout=10000)
    else:
        # the walkthrough, which never highlights the hidden sidebar
        p.get_by_text(f"1 of {len(TITLES)}").wait_for(timeout=10000)
        assert p.locator(".driver-active-element").count() == 0
        p.get_by_role("dialog").get_by_role("button", name="Skip").click()
    assert p.evaluate("() => window.localStorage.getItem('stockadvisor-tour-seen')") == "1"

    # the choice is remembered on refresh and on a later visit in the same browser
    for _ in range(2):
        v.open()
        assert wait_for_welcome(p, seconds=5) is None
        assert v.button("Take a tour").is_visible()
    v.assert_clean()


def test_skipping_the_welcome_is_remembered(visitor):
    v = visitor(PHONE)
    p = v.page
    skip_welcome(v)
    v.open()
    assert wait_for_welcome(p, seconds=5) is None
    v.assert_clean()


def test_first_visit_welcome_inside_an_iframe(browser, app_url):
    """Streamlit Community Cloud and portfolio sites show the app inside an iframe."""
    context = browser.new_context(viewport=DESKTOP)
    page = context.new_page()
    page.set_content(f'<iframe src="{app_url}" style="border:0;width:100%;height:880px" '
                     'sandbox="allow-forms allow-modals allow-popups allow-same-origin allow-scripts '
                     'allow-downloads"></iframe>')
    frame = page.frame_locator("iframe")
    frame.get_by_text("Your portfolio").wait_for(timeout=60000)
    assert wait_for_welcome(page, frame=frame) is not None
    context.close()


def test_desktop_spotlight_tour(visitor):
    v = visitor()
    p = v.page
    welcome = wait_for_welcome(p)
    assert welcome is not None, "a first-time visitor should see the welcome dialog without clicking anything"
    inputs_before = p.evaluate(SIDEBAR_INPUTS)

    v.button("Start the tour").click()
    assert v.popover_progress() == f"1 of {len(TITLES)}"
    assert p.locator(".driver-popover-prev-btn").inner_text() == "Back"
    p.locator(".driver-popover-next-btn").click()
    assert v.popover_progress() == f"2 of {len(TITLES)}"
    p.locator(".driver-popover-prev-btn").click()
    assert v.popover_progress() == f"1 of {len(TITLES)}"

    for i, title in enumerate(TITLES):
        if i:
            p.locator(".driver-popover-next-btn").click()
        assert v.popover_progress() == f"{i + 1} of {len(TITLES)}"
        assert p.locator(".driver-popover-title").inner_text() == title
        if i < len(TARGETS):
            # each step highlights its own section, scrolled into view
            key, in_sidebar = TARGETS[i]
            assert highlighted_key(p) == key
            assert_highlight_on_screen(p, in_sidebar)
        else:
            assert highlighted_key(p) is None  # the finish card highlights nothing
        if title == "Set up the portfolio":
            assert p.locator(".driver-active-element").get_by_text("Allocations (%)").count() == 1
        if title == "Compare strategies":
            text = p.locator(".driver-popover-description").inner_text()
            assert "Always Cash" in text and "Always Hold" in text and "not a prediction" in text
        if title == "Check and run":
            assert "chart of portfolio value" in p.locator(".driver-popover-description").inner_text()
            assert p.locator(".driver-active-element").get_by_role("button", name="Run simulation").count() == 1

    assert p.locator(".driver-popover-next-btn").inner_text() == "Done"
    p.locator(".driver-popover-next-btn").click()
    p.locator(".driver-popover").wait_for(state="detached", timeout=10000)

    # the tour never changes inputs or runs a simulation
    p.wait_for_timeout(1000)
    assert p.evaluate(SIDEBAR_INPUTS) == inputs_before
    assert p.locator(".js-plotly-plot").count() == 0

    # the welcome card does not come back after a refresh, but the tour can be replayed
    v.open()
    assert p.get_by_text(WELCOME).count() == 0
    assert v.button("Take a tour").is_visible()
    v.assert_clean()


def test_tour_can_be_dismissed_any_time(visitor):
    v = visitor()
    p = v.page
    wait_for_welcome(p)
    p.keyboard.press("Escape")  # closing the welcome dialog counts as skipping
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
    skip_welcome(v)
    v.button("Run simulation").click()
    p.get_by_text(RESULTS_TITLE).wait_for(timeout=120000)

    v.button("Take a tour").click()
    v.popover_progress()
    for i in range(1, TITLES_WITH_RESULTS.index("Read the results") + 1):
        p.locator(".driver-popover-next-btn").click()
        assert v.popover_progress() == f"{i + 1} of {len(TITLES_WITH_RESULTS)}"
    assert p.locator(".driver-popover-title").inner_text() == "Read the results"
    assert highlighted_key(p) == "st-key-tour_results"
    highlighted = p.locator(".driver-active-element")
    assert highlighted.get_by_role("tab", name="Jul 10 – Jul 18, 2024").count() == 1  # the result tabs
    box = p.evaluate(HIGHLIGHT_BOX)
    assert box["left"] > p.locator('[data-testid="stSidebar"]').bounding_box()["width"]
    assert box["top"] < box["vh"] and box["bottom"] > 0
    p.keyboard.press("Escape")
    p.locator(".js-plotly-plot").nth(3).wait_for(state="attached", timeout=20000)  # results unchanged by the tour
    assert p.locator(".js-plotly-plot").count() == 4
    v.assert_clean()


def run_walkthrough(v, titles=TITLES):
    p = v.page
    dialog = p.get_by_role("dialog")
    dialog.wait_for(timeout=20000)
    p.wait_for_timeout(500)
    assert p.locator(".driver-popover").count() == 0
    assert p.locator(".driver-active-element").count() == 0
    total = len(titles)
    assert f"1 of {total}" in dialog.inner_text() and titles[0] in dialog.inner_text()

    dialog.get_by_role("button", name="Next").click()
    p.get_by_text(f"2 of {total}").wait_for(timeout=10000)
    dialog.get_by_role("button", name="Back").click()
    p.get_by_text(f"1 of {total}").wait_for(timeout=10000)
    for n in range(2, total + 1):
        dialog.get_by_role("button", name="Next").click()
        p.get_by_text(f"{n} of {total}").wait_for(timeout=20000)
        assert titles[n - 1] in dialog.inner_text()
        if titles[n - 1] == "Compare strategies":
            assert "Dory" in dialog.inner_text() and "not a prediction" in dialog.inner_text()
    dialog.get_by_role("button", name="Done").click()
    dialog.wait_for(state="detached", timeout=10000)
    assert p.locator(".driver-active-element").count() == 0


def test_narrow_viewport_uses_walkthrough(visitor):
    v = visitor(PHONE)
    p = v.page
    inputs_before = p.evaluate(SIDEBAR_INPUTS)
    assert wait_for_welcome(p) is not None
    v.button("Start the tour").click()
    p.get_by_text(f"1 of {len(TITLES)}").wait_for(timeout=10000)
    assert "Tap » at the top left" in p.get_by_role("dialog").inner_text()
    run_walkthrough(v)
    assert p.locator(".js-plotly-plot").count() == 0
    assert p.evaluate(SIDEBAR_INPUTS) == inputs_before

    # skip from the middle of the walkthrough ("Take a tour" is also in the main area, visible on phones)
    v.button("Take a tour").click()
    dialog = p.get_by_role("dialog")
    dialog.get_by_role("button", name="Next").click()
    p.get_by_text(f"2 of {len(TITLES)}").wait_for(timeout=10000)
    dialog.get_by_role("button", name="Skip").click()
    dialog.wait_for(state="detached", timeout=10000)

    v.open()
    assert p.get_by_text(WELCOME).count() == 0
    v.assert_clean()


def open_phone_sidebar(page):
    page.get_by_test_id("stExpandSidebarButton").click()
    page.wait_for_timeout(800)


def test_narrow_viewport_walkthrough_with_results(visitor):
    v = visitor(PHONE)
    p = v.page
    skip_welcome(v)
    v.button("Run simulation").click()  # in the main area, no need to open the sidebar
    p.get_by_text(RESULTS_TITLE).wait_for(timeout=120000)
    p.wait_for_timeout(1500)
    v.button("Take a tour").click()
    run_walkthrough(v, TITLES_WITH_RESULTS)
    assert p.locator(".js-plotly-plot").count() == 4
    v.assert_clean()


def results_heading_in_view(page):
    box = page.get_by_role("heading", name=RESULTS_TITLE).bounding_box()
    return box is not None and 0 <= box["y"] < page.viewport_size["height"] / 2


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_run_scrolls_to_results_and_settings_update_summary(visitor, viewport):
    v = visitor(viewport)
    p = v.page
    skip_welcome(v)
    if viewport is PHONE:
        open_phone_sidebar(p)
    value = p.get_by_label("Initial portfolio value (USD)")
    value.fill("2500")
    value.press("Enter")
    p.get_by_text("Starting value $2,500").wait_for(timeout=10000)
    if viewport is PHONE:
        p.get_by_test_id("stSidebarCollapseButton").locator("button").click()
        p.wait_for_timeout(800)

    v.button("Run simulation").click()
    p.get_by_text(RESULTS_TITLE).wait_for(timeout=120000)
    for _ in range(20):  # the page scrolls smoothly to the results
        if results_heading_in_view(p):
            break
        p.wait_for_timeout(250)
    assert results_heading_in_view(p)
    assert p.locator(".js-plotly-plot").count() == 4
    assert p.get_by_role("tab").count() == 4
    p.get_by_role("tab", name="Last 26 weeks").click()
    p.wait_for_timeout(500)
    assert p.get_by_text("of $2,500, tested with").is_visible()  # what was simulated
    v.assert_clean()


def test_reset_demo_restores_defaults_on_phone(visitor):
    v = visitor(PHONE)
    p = v.page
    skip_welcome(v)
    open_phone_sidebar(p)
    value = p.get_by_label("Initial portfolio value (USD)")
    value.fill("4000")
    value.press("Enter")
    p.get_by_text("Starting value $4,000").wait_for(timeout=10000)
    v.button("Reset demo").click()
    p.get_by_text("Starting value $1,000").wait_for(timeout=10000)
    assert p.get_by_text(WELCOME).count() == 0  # the tour choice is kept
    v.assert_clean()


def test_tour_cards_follow_dark_theme(browser, app_url):
    context = browser.new_context(viewport=DESKTOP, color_scheme="dark")
    p = context.new_page()
    p.goto(app_url, wait_until="networkidle")
    p.get_by_text("Your portfolio").wait_for(timeout=60000)
    p.wait_for_timeout(2500)
    p.get_by_role("button", name="Start the tour").click()
    p.locator(".driver-popover").wait_for(timeout=20000)
    background = p.locator(".driver-popover").evaluate("e => getComputedStyle(e).backgroundColor")
    assert background == "rgb(38, 39, 48)"
    context.close()


def test_collapsed_sidebar_on_desktop_uses_walkthrough(visitor):
    v = visitor()
    p = v.page
    skip_welcome(v)
    p.get_by_test_id("stSidebar").hover()
    p.get_by_test_id("stSidebarCollapseButton").locator("button").click()
    p.wait_for_timeout(2000)
    v.button("Take a tour").click()  # the main-area link, while the sidebar is hidden
    run_walkthrough(v)
    v.assert_clean()


def test_shrinking_window_mid_tour_never_highlights_hidden_controls(visitor):
    v = visitor()
    p = v.page
    v.button("Start the tour").click()
    v.popover_progress()
    p.locator(".driver-popover-next-btn").click()
    assert v.popover_progress() == f"2 of {len(TITLES)}"

    p.set_viewport_size(PHONE)
    dialog = p.get_by_role("dialog")
    dialog.wait_for(timeout=20000)
    assert TITLES[1] in dialog.inner_text()  # continues at the same step
    p.wait_for_timeout(1000)
    assert p.locator(".driver-popover").count() == 0
    assert p.locator(".driver-active-element").count() == 0
    v.assert_clean()


def test_app_works_when_tour_component_fails_to_load(visitor):
    v = visitor(block_tour_component=True)
    p = v.page
    v.button("Start the tour").click()
    p.wait_for_timeout(2000)
    v.button("Run simulation").click()
    p.get_by_text(RESULTS_TITLE).wait_for(timeout=120000)
    p.wait_for_timeout(2000)
    assert p.locator(".js-plotly-plot").count() == 4
    assert p.locator('[data-testid="stException"]').count() == 0
    assert not v.external_requests

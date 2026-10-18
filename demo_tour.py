"""
Optional onboarding tour for the public demo.

- Desktop: a spotlight tour (streamlit-tour / Driver.js) that highlights the sidebar controls.
- Narrow screens, a hidden sidebar, or if the tour component is unavailable: a native Streamlit dialog walkthrough
  that never highlights anything.

A small helper component reports the viewport width, whether the sidebar controls are actually on screen, and whether
this browser has already seen the welcome card (a single "seen" flag in localStorage, no personal information).
The tour only explains the interface. It never clicks buttons, runs simulations, sends emails or calls external APIs.
"""
import logging
import re
import streamlit as st

try:
    from streamlit_tour import Tour
except Exception:  # the app keeps working without the tour package
    Tour = None

logger = logging.getLogger(__name__)

# keys of the containers that wrap the existing controls in main.py
PAGES_KEY = "tour_pages"
INPUTS_KEY = "tour_inputs"
SIMULATION_KEY = "tour_simulation"
PORTFOLIO_KEY = "tour_portfolio"
ADVISORS_KEY = "tour_advisors"
RUN_KEY = "tour_run"  # the "Your simulation" summary and Run simulation button
RESULTS_KEY = "tour_results"  # wraps the result tabs

SPOTLIGHT_MIN_WIDTH = 768  # below this, Streamlit shows the sidebar as an overlay

WELCOME_TEXT = "Want a quick walkthrough of the settings and strategies?"

# step text uses **bold** and line breaks, shown as markdown in the walkthrough and as HTML in the spotlight tour
# (title, text, container key or None, control lives in the sidebar)
PAGES_STEP = (
    "Two pages",
    "**Simulator**, where you are now, compares the strategies. **Email Settings** is where you'd schedule a "
    "daily email report. In this demo it only keeps your settings for this visit and never sends email.",
    PAGES_KEY, True)
PORTFOLIO_STEP = (
    "Set up the portfolio",
    "**Initial portfolio value** is the total you start with, and the **allocations** split it between the stocks "
    "and cash. The example puts $1,000 50/50 into AAPL and NVDA, so each gets $500. They need to add up to 100%.",
    PORTFOLIO_KEY, True)
INPUTS_STEP = (
    "Choose stocks and data",
    "Pick the stocks and the range of price data to use. The demo has daily AAPL and NVDA prices from January 2023 "
    "to September 2024, and I've already filled in an example. The allocations above follow the stocks you enter.",
    INPUTS_KEY, True)
SIMULATION_STEP = (
    "Pick what to test",
    "The test dates choose which stretch of that data the strategies are tested on, so they need to fall inside "
    "the data range. **Extra test periods** add tests over the last 1, 4 and 26 weeks of the data, each with its "
    "own results.",
    SIMULATION_KEY, True)
ADVISORS_STEP = (
    "Compare strategies",
    "**Always Cash** sells everything on the first day and holds cash.\n"
    "**Always Hold** keeps the starting shares and never trades.\n"
    "**Dory** moves everything into the stock that rose most from open to close that day, or into cash if none "
    "rose. It uses that day's closing prices, which you only know once the day is over, so treat it as a "
    "hindsight benchmark, not a prediction.",
    ADVISORS_KEY, True)
RUN_STEP = (
    "Check and run",
    "This summary follows your settings, and \"How the strategies work\" has the details. Click "
    "**Run simulation** to test the selected strategies. For each test window you'll get a chart of portfolio "
    "value over time and a table with each strategy's final value and % return.",
    RUN_KEY, False)
RESULTS_STEP = (
    "Read the results",
    "The table above compares every strategy's % return across the test windows. Each tab is one window: the "
    "chart shows portfolio value day by day, the table has final value and % return (\"Initial\" is the "
    "starting point), and \"View daily data\" shows the daily holdings.",
    RESULTS_KEY, False)
FINISH_STEP = (
    "You're all set!",
    "Try different stocks, allocations, dates or strategies and run it again to see how the results change. "
    "You can replay this tour anytime with \"Take a tour\" at the bottom of the sidebar.",
    None, False)


def steps_for(has_results):
    """The tour steps in page order. The results step is only included when there are results to highlight."""
    steps = [PAGES_STEP, PORTFOLIO_STEP, INPUTS_STEP, SIMULATION_STEP, ADVISORS_STEP, RUN_STEP]
    if has_results:
        steps.append(RESULTS_STEP)
    return steps + [FINISH_STEP]


def _as_html(text):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text).replace("\n", "<br>")


def _as_markdown(text):
    return text.replace("\n", "  \n")


ENV_JS = """
export default function (component) {
  const { data, setStateValue, parentElement } = component;
  const STORAGE_KEY = "stockadvisor-tour-seen";
  let store = null;
  try { store = window.localStorage; } catch (e) { store = null; }
  // "seen" is read once per page load, so remembering a choice never triggers an extra rerun
  if (parentElement.__stockadvisorTourSeen === undefined) {
    try { parentElement.__stockadvisorTourSeen = !!store && store.getItem(STORAGE_KEY) === "1"; }
    catch (e) { parentElement.__stockadvisorTourSeen = false; }
  }
  if (data && data.mark_seen && store) {
    try { store.setItem(STORAGE_KEY, "1"); } catch (e) {}
  }
  // tour cards follow the app theme
  document.body.classList.toggle("stockadvisor-dark", !!(data && data.dark));
  // bring new simulation results into view once
  if (data && data.scroll_to && parentElement.__stockadvisorScrolled !== data.scroll_to) {
    parentElement.__stockadvisorScrolled = data.scroll_to;
    setTimeout(() => {
      const results = document.querySelector(".st-key-results_section");
      if (results) results.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 300);
  }
  const measure = () => {
    const width = window.innerWidth;
    const target = document.querySelector(".st-key-%(pages)s");  // the first sidebar control
    let sidebarVisible = false;
    if (target) {
      const r = target.getBoundingClientRect();
      sidebarVisible = r.width > 0 && r.height > 0 && r.left >= 0 && r.right <= width;
    }
    // only values the tour uses, so ordinary resizing or opening the sidebar on a phone does not cause reruns
    return { spotlight: sidebarVisible && width >= %(min_width)d, seen: parentElement.__stockadvisorTourSeen };
  };
  const report = () => {
    const env = measure();
    const json = JSON.stringify(env);
    if (parentElement.__stockadvisorTourEnv !== json) {
      parentElement.__stockadvisorTourEnv = json;
      setStateValue("env", env);  // Python switches an active spotlight tour to the walkthrough
    } else if (!env.spotlight && document.querySelector(".driver-popover")) {
      // then close the leftover spotlight card (Driver.js closes on Escape)
      window.dispatchEvent(new KeyboardEvent("keyup", { key: "Escape", bubbles: true }));
    }
  };
  report();
  const timer = setInterval(report, 700);
  return () => clearInterval(timer);
}
""" % {"pages": PAGES_KEY, "min_width": SPOTLIGHT_MIN_WIDTH}

# compact tour cards that match the Streamlit look (Driver.js class names)
TOUR_CSS = """
body .driver-popover {
  font-family: "Source Sans", "Source Sans Pro", sans-serif;
  color: #31333f;
  border-radius: 12px;
  padding: 16px 18px 14px;
  max-width: 320px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.16);
}
body .driver-popover-title { font: inherit; font-size: 1rem; font-weight: 600; }
body .driver-popover-description b { font-family: inherit; font-weight: 600; }
body .driver-popover-description { font: inherit; font-size: 0.9rem; line-height: 1.45; margin-top: 6px; }
body .driver-popover-progress-text { font-size: 0.8rem; color: #6b6f7b; }
body .driver-popover-footer { margin-top: 14px; }
body .driver-popover-footer button {
  font: inherit; font-size: 0.85rem; text-shadow: none;
  border-radius: 8px; padding: 3px 10px; border: 1px solid #d5d6da;
}
body .driver-popover-footer .driver-popover-next-btn { background: #ff4b4b; border-color: #ff4b4b; color: #fff; }
body .driver-popover-close-btn { color: #6b6f7b; }
/* keep the results heading clear of the app toolbar when scrolled into view */
.st-key-results_section { scroll-margin-top: 4rem; }
body.stockadvisor-dark .driver-popover { background: #262730; color: #fafafa; box-shadow: 0 6px 24px rgba(0, 0, 0, 0.5); }
body.stockadvisor-dark .driver-popover-arrow { border-color: #262730; }
body.stockadvisor-dark .driver-popover-progress-text,
body.stockadvisor-dark .driver-popover-close-btn { color: #a3a8b8; }
body.stockadvisor-dark .driver-popover-footer button { background: #0e1117; color: #fafafa; border-color: #4a4d57; }
"""

try:
    _env_component = st.components.v2.component("stockadvisor_tour_env", js=ENV_JS, css=TOUR_CSS,
                                                 isolate_styles=False)
except Exception:
    logger.exception("Tour helper component could not be registered")
    _env_component = None


def _session_seen():
    return st.session_state.get("tour_seen", False)


def mount_env(scroll_to=None):
    """
    Mount the invisible browser helper and return the environment dict, or None if it is not known (yet).
    scroll_to: a new value scrolls the page to the simulation results once.
    """
    if _env_component is None:
        return None
    try:
        dark = st.context.theme.type == "dark"
    except Exception:
        dark = False
    try:
        result = _env_component(key="tour_env", data={"mark_seen": _session_seen(), "dark": dark,
                                                      "scroll_to": scroll_to},
                                default={"env": None}, height=0, on_env_change=lambda: None)
        return result.env
    except Exception:
        logger.exception("Tour helper component failed")
        return None


def _start():
    # run() decides between the spotlight tour and the walkthrough, using the current viewport
    st.session_state.tour_seen = True
    st.session_state.tour_requested = True


def _skip():
    st.session_state.tour_seen = True


def render_welcome(env):
    """The welcome card for first-time visitors."""
    if env is not None and not env.get("seen") and not _session_seen():
        with st.container(border=True, key="tour_welcome"):
            st.markdown(WELCOME_TEXT)
            with st.container(horizontal=True):
                st.button("Start tour", type="primary", on_click=_start, key="tour_start")
                st.button("No thanks", type="tertiary", on_click=_skip, key="tour_skip")


def render_replay_button():
    st.button("Take a tour", type="tertiary", icon=":material/explore:", on_click=_start, key="tour_replay")


def _sidebar_hint(env):
    if env is None:
        return "You'll find this in the sidebar."
    return "This is in the sidebar. Tap » at the top left to open it."


def _end_walkthrough():
    st.session_state.tour_walk_active = False


@st.dialog("Quick tour", width="small", on_dismiss=_end_walkthrough)
def _walkthrough(env, has_results):
    steps = steps_for(has_results)
    step = min(st.session_state.get("tour_walk_step", 0), len(steps) - 1)
    title, text, _, in_sidebar = steps[step]
    last = step == len(steps) - 1

    st.caption(f"{step + 1} of {len(steps)}")
    st.markdown(f"**{title}**")
    st.markdown(_as_markdown(text))
    if in_sidebar:
        st.caption(_sidebar_hint(env))

    with st.container(horizontal=True):
        if st.button("Back", disabled=step == 0, key="tour_walk_back"):
            st.session_state.tour_walk_step = step - 1
            st.rerun(scope="fragment")
        if st.button("Done" if last else "Next", type="primary", key="tour_walk_next"):
            if last:
                _end_walkthrough()
                st.rerun()
            st.session_state.tour_walk_step = step + 1
            st.rerun(scope="fragment")
        if not last and st.button("Skip", type="tertiary", key="tour_walk_skip"):
            _end_walkthrough()
            st.rerun()


def _spotlight_steps(has_results):
    steps = []
    tour_steps = steps_for(has_results)
    for i, (title, text, key, in_sidebar) in enumerate(tour_steps):
        if key:
            step = Tour.bind(key, title=title, desc=_as_html(text), side="right" if in_sidebar else None)
        else:
            step = Tour.info(title=title, desc=_as_html(text))  # centered card, nothing highlighted
        # Driver.js button labels, matching the walkthrough
        step.popover.update(prevBtnText="Back", nextBtnText="Done" if i == len(tour_steps) - 1 else "Next")
        steps.append(step)
    return steps


def run(env, has_results):
    """Show the active tour, if any. Call this at the end of the page so every highlighted control exists."""
    spotlight_ok = bool(env and env.get("spotlight"))

    requested = st.session_state.pop("tour_requested", False)
    use_spotlight = Tour is not None and spotlight_ok and not st.session_state.get("tour_spotlight_failed")
    if requested and use_spotlight:
        # a fresh component key for every run, so the previous run's "dismissed" state cannot end the new one
        st.session_state.tour_run_count = st.session_state.get("tour_run_count", 0) + 1
        st.session_state.tour_spotlight_pending = True
    elif requested:
        st.session_state.tour_walk_step = 0
        st.session_state.tour_walk_active = True

    if Tour is not None and not st.session_state.get("tour_spotlight_failed"):
        try:
            tour = Tour(_spotlight_steps(has_results), key=f"tour_spotlight_{st.session_state.get('tour_run_count', 0)}",
                        overlay_opacity=0.35)
            active = st.session_state.get(tour.state_key, False)
            if active and not spotlight_ok:
                # the sidebar was hidden or the window became narrow: continue without highlighting
                st.session_state[tour.state_key] = False
                st.session_state.tour_walk_step = tour.result.currentStep if tour.result else 0
                st.session_state.tour_walk_active = True
                st.rerun()
            if st.session_state.pop("tour_spotlight_pending", False):
                tour.start()
        except Exception:
            logger.exception("Spotlight tour failed, using the walkthrough instead")
            st.session_state.tour_spotlight_failed = True
            if st.session_state.pop("tour_spotlight_pending", False):
                st.session_state.tour_walk_step = 0
                st.session_state.tour_walk_active = True

    if st.session_state.get("tour_walk_active"):
        _walkthrough(env, has_results)


def is_tour_key(key):
    """Session keys that survive "Reset Demo", so the welcome card does not come back."""
    return key.startswith(("tour_", "stTour-"))

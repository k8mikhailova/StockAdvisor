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
import streamlit as st

try:
    from streamlit_tour import Tour
except Exception:  # the app keeps working without the tour package
    Tour = None

logger = logging.getLogger(__name__)

# keys of the containers that wrap the existing controls in main.py
INPUTS_KEY = "tour_inputs"
ADVISORS_KEY = "tour_advisors"
RUN_KEY = "tour_run"
RESULTS_KEY = "tour_results"  # wraps the first result section

SPOTLIGHT_MIN_WIDTH = 768  # below this, Streamlit shows the sidebar as an overlay

WELCOME_TEXT = ("StockAdvisor lets you compare simple investment strategies using historical stock data. "
                "Want a quick walkthrough?")

# (title, text, container key or None, control lives in the sidebar)
STEPS = [
    ("Choose your stocks",
     "Pick the stocks and time period you want to explore. The demo includes AAPL and NVDA prices from 2023 to 2024, "
     "and I've already filled in an example to get you started.", INPUTS_KEY, True),
    ("Compare strategies",
     "Each advisor follows a different approach to managing the portfolio. Select the ones you'd like to compare.",
     ADVISORS_KEY, True),
    ("Run a simulation",
     "Click Run Simulation to see how the selected strategies perform when they start with the same portfolio "
     "($1,000 by default).", RUN_KEY, True),
    ("Explore the results",
     "Once you run a simulation, you can compare the portfolio values, returns, and charts for each strategy.",
     RESULTS_KEY, False),
    ("You're all set!",
     "Try changing the stocks, dates, or strategies to see how the results change. "
     "You can replay this tour anytime with \"Take a tour\".", None, False),
]

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
  const measure = () => {
    const width = window.innerWidth;
    const target = document.querySelector(".st-key-%(inputs)s");
    let sidebarVisible = false;
    if (target) {
      const r = target.getBoundingClientRect();
      sidebarVisible = r.width > 0 && r.height > 0 && r.left >= 0 && r.right <= width;
    }
    return { width: width, sidebar_visible: sidebarVisible,
             spotlight: sidebarVisible && width >= %(min_width)d, seen: parentElement.__stockadvisorTourSeen };
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
""" % {"inputs": INPUTS_KEY, "min_width": SPOTLIGHT_MIN_WIDTH}

# compact tour cards that match the Streamlit look (Driver.js class names)
TOUR_CSS = """
body .driver-popover {
  font-family: "Source Sans", "Source Sans Pro", sans-serif;
  color: #31333f;
  border-radius: 12px;
  padding: 16px 18px 14px;
  max-width: 300px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.16);
}
body .driver-popover-title { font: inherit; font-size: 1rem; font-weight: 600; }
body .driver-popover-description { font: inherit; font-size: 0.9rem; line-height: 1.45; margin-top: 6px; }
body .driver-popover-progress-text { font-size: 0.8rem; color: #6b6f7b; }
body .driver-popover-footer { margin-top: 14px; }
body .driver-popover-footer button {
  font: inherit; font-size: 0.85rem; text-shadow: none;
  border-radius: 8px; padding: 3px 10px; border: 1px solid #d5d6da;
}
body .driver-popover-footer .driver-popover-next-btn { background: #ff4b4b; border-color: #ff4b4b; color: #fff; }
body .driver-popover-close-btn { color: #6b6f7b; }
"""

try:
    _env_component = st.components.v2.component("stockadvisor_tour_env", js=ENV_JS, css=TOUR_CSS,
                                                 isolate_styles=False)
except Exception:
    logger.exception("Tour helper component could not be registered")
    _env_component = None


def _session_seen():
    return st.session_state.get("tour_seen", False)


def mount_env():
    """Mount the invisible helper and return the browser environment dict, or None if it is not known (yet)."""
    if _env_component is None:
        return None
    try:
        result = _env_component(key="tour_env", data={"mark_seen": _session_seen()}, default={"env": None},
                                height=0, on_env_change=lambda: None)
        return result.env
    except Exception:
        logger.exception("Tour helper component failed")
        return None


def _start(env):
    st.session_state.tour_seen = True
    if Tour is not None and env and env.get("spotlight") and not st.session_state.get("tour_spotlight_failed"):
        # a fresh component key for every run, so the previous run's "dismissed" state cannot end the new one
        st.session_state.tour_run_count = st.session_state.get("tour_run_count", 0) + 1
        st.session_state.tour_spotlight_pending = True
    else:
        st.session_state.tour_walk_step = 0
        st.session_state.tour_walk_active = True


def _skip():
    st.session_state.tour_seen = True


def render_entry(env):
    """The welcome card for first-time visitors, otherwise a small "Take a tour" button."""
    show_welcome = env is not None and not env.get("seen") and not _session_seen()
    if show_welcome:
        with st.container(border=True, key="tour_welcome"):
            st.markdown(WELCOME_TEXT)
            with st.container(horizontal=True):
                st.button("Start tour", type="primary", on_click=_start, args=(env,), key="tour_start")
                st.button("No thanks", type="tertiary", on_click=_skip, key="tour_skip")
    else:
        st.button("Take a tour", type="tertiary", icon=":material/explore:", on_click=_start, args=(env,),
                  key="tour_replay")


def _sidebar_hint(env):
    if env and env.get("sidebar_visible"):
        return "You'll find this in the sidebar on the left."
    return "This is in the sidebar. Tap » at the top left to open it."


def _end_walkthrough():
    st.session_state.tour_walk_active = False


@st.dialog("Quick tour", width="small", on_dismiss=_end_walkthrough)
def _walkthrough(env):
    step = st.session_state.get("tour_walk_step", 0)
    title, text, _, in_sidebar = STEPS[step]
    last = step == len(STEPS) - 1

    st.caption(f"{step + 1} of {len(STEPS)}")
    st.markdown(f"**{title}**")
    st.write(text)
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
    for i, (title, text, key, in_sidebar) in enumerate(STEPS):
        if key and (key != RESULTS_KEY or has_results):
            step = Tour.bind(key, title=title, desc=text, side="right" if in_sidebar else "left")
        else:
            step = Tour.info(title=title, desc=text)  # centered card, nothing highlighted
        # Driver.js button labels, matching the walkthrough
        step.popover.update(prevBtnText="Back", nextBtnText="Done" if i == len(STEPS) - 1 else "Next")
        steps.append(step)
    return steps


def run(env, has_results):
    """Show the active tour, if any. Call this at the end of the page so every highlighted control exists."""
    spotlight_ok = bool(env and env.get("spotlight"))

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
        _walkthrough(env)


def is_tour_key(key):
    """Session keys that survive "Reset Demo", so the welcome card does not come back."""
    return key.startswith(("tour_", "stTour-"))

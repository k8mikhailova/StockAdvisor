"""
Streamlit AppTest checks for the public demo mode.
Run with:  pip install -r requirements.txt pytest  &&  python -m pytest tests
"""
import hashlib
import os
import smtplib
import subprocess

import pandas as pd
import pytest
import requests
from streamlit.testing.v1 import AppTest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(APP_DIR, "main.py")


def repository_file_hashes():
    files = subprocess.run(["git", "ls-files"], cwd=APP_DIR, capture_output=True, text=True).stdout.split()
    files += ["email_settings.json", "parameters.json"]  # files the app writes in live mode
    return {f: hashlib.sha256(open(os.path.join(APP_DIR, f), "rb").read()).hexdigest()
            for f in files if os.path.isfile(os.path.join(APP_DIR, f))}


@pytest.fixture(autouse=True)
def no_credentials_network_or_email(monkeypatch):
    """Demo mode must work without credentials and must never call external APIs or send emails."""
    for name in ["FMP_API_KEY", "EMAIL_ADDRESS", "EMAIL_PASSWORD", "STOCKADVISOR_MODE"]:
        monkeypatch.delenv(name, raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("external request or email attempted in demo mode")

    monkeypatch.setattr(requests, "get", blocked)
    monkeypatch.setattr(requests.Session, "request", blocked)
    monkeypatch.setattr(smtplib, "SMTP", blocked)
    monkeypatch.setattr(smtplib, "SMTP_SSL", blocked)


@pytest.fixture(autouse=True)
def repository_files_unchanged():
    before = repository_file_hashes()
    yield
    assert repository_file_hashes() == before, "demo mode modified files in the repository"


def start_app():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    return at


def click(at, label):
    [b for b in at.button if b.label == label][0].click().run()
    assert not at.exception, at.exception


def run_simulation(at):
    at.button(key="run_simulation").click().run()
    assert not at.exception, at.exception


def portfolio_line(at):
    return next(m.value for m in at.markdown if m.value.startswith("Starting value"))


def test_app_starts_in_demo_mode():
    at = start_app()
    assert at.title[0].value == "StockAdvisor"
    assert any("Demo data" in c.value for c in at.caption)
    assert at.text_input(key="set_tickers").value == "AAPL, NVDA"
    assert portfolio_line(at) == "Starting value **$1,000** · Stocks **AAPL, NVDA** · **3 of 3** strategies selected"
    assert [m.value for m in at.main.markdown if m.value.startswith("#### ")] == ["#### Your portfolio",
                                                                                "#### Compare strategies"]
    assert any(c.value.startswith("Test windows: Jul 10 – Jul 18, 2024") for c in at.caption)
    assert [e.label for e in at.expander] == ["How the strategies work"]
    page_text = " ".join(m.value for m in at.markdown)
    assert "no-risk" not in page_text and "hindsight benchmark" in page_text
    assert not at.error
    # one simulation action, in the main area
    assert [b.label for b in at.button].count("Run simulation") == 1
    assert not [b for b in at.sidebar.button if b.label.lower().startswith("run")]


def test_demo_hides_controls_that_do_nothing():
    at = start_app()
    labels = [w.label for w in list(at.number_input) + list(at.checkbox)]
    assert not [label for label in labels if "Commission" in label or "tax" in label.lower()]
    assert "Update Email Parameters" not in labels


def test_summary_follows_the_settings():
    at = start_app()
    at.number_input(key="set_value").set_value(2500).run()
    at.checkbox(key="adv_dory").uncheck().run()
    assert "**$2,500**" in portfolio_line(at) and "**2 of 3**" in portfolio_line(at)
    assert any(c.value == "Not selected: Dory" for c in at.caption)

    # the allocations follow the stock symbols
    at.text_input(key="set_tickers").set_value("AAPL").run()
    assert "Stocks **AAPL** ·" in portfolio_line(at)
    assert "alloc_NVDA" not in [n.key for n in at.number_input]
    assert any("add up to 50%" in e.value for e in at.sidebar.error)
    at.number_input(key="alloc_AAPL").set_value(70).run()
    at.number_input(key="alloc_Cash").set_value(30).run()
    assert not at.error
    assert any("AAPL 70%" in m.value and "Cash 30%" in m.value for m in at.markdown)

    at.text_input(key="set_periods").set_value("2").run()
    assert any("the last 2 weeks of data" in c.value for c in at.caption)


def test_run_simulation_renders_all_strategies():
    at = start_app()
    run_simulation(at)

    assert [h.value for h in at.main.header] == ["Simulation results"]
    assert [t.label for t in at.tabs] == ["Jul 10 – Jul 18, 2024", "Last 1 week", "Last 4 weeks", "Last 26 weeks"]
    assert len(at.get("plotly_chart")) == 4
    assert not at.error

    # the comparison table shows each strategy's % return in every test window
    comparison = at.dataframe[0].value
    assert list(comparison.columns) == ["Strategy", "Jul 10 – Jul 18, 2024", "Last 1 week", "Last 4 weeks",
                                        "Last 26 weeks"]
    assert list(comparison["Strategy"]) == ["Always Cash", "Always Hold", "Dory"]

    # the first tab's summary table matches the results committed in the repository
    summary = at.dataframe[1].value
    assert {"Always Cash", "Always Hold", "Dory"} <= set(summary["Advisor"])
    reference = pd.read_csv(os.path.join(APP_DIR, "simulation_results_1.csv"))
    expected_dory = reference[reference["Advisor"] == "dory"].iloc[-1]["Portfolio Value USD"]
    actual_dory = summary[summary["Advisor"] == "Dory"].iloc[0]["Final Portfolio Value"]
    assert actual_dory == pytest.approx(expected_dory, abs=1e-3)
    expected_return = round((expected_dory - 1000) / 1000 * 100, 2)
    assert comparison.set_index("Strategy").loc["Dory", "Jul 10 – Jul 18, 2024"] == pytest.approx(expected_return)

    # results stay visible when other inputs change, with a note that they are out of date
    at.number_input(key="set_value").set_value(2000).run()
    assert len(at.get("plotly_chart")) == 4
    assert any("settings have changed" in c.value for c in at.caption)

    # run again with the new settings
    run_simulation(at)
    assert not any("settings have changed" in c.value for c in at.caption)
    assert at.dataframe[1].value.iloc[0]["Final Portfolio Value"] == 2000


def test_invalid_inputs_show_errors_not_exceptions():
    at = start_app()
    at.text_input(key="set_tickers").set_value("AAPL, TSLA").run()
    assert any("TSLA" in e.value for e in at.sidebar.error)
    run_simulation(at)
    assert any("fix the ticker symbols" in e.value for e in at.main.error)
    assert not at.get("plotly_chart")

    at = start_app()
    at.text_input(key="set_periods").set_value("1, abc").run()
    run_simulation(at)
    assert any("whole numbers" in e.value for e in at.main.error)

    at = start_app()
    at.number_input(key="alloc_AAPL").set_value(40).run()
    run_simulation(at)
    assert any("must sum to 100%" in e.value for e in at.main.error)

    at = start_app()
    for advisor in ["always_cash", "always_hold", "dory"]:
        at.checkbox(key=f"adv_{advisor}").uncheck().run()
    run_simulation(at)
    assert any("at least one advisor" in e.value for e in at.main.error)

    at = start_app()
    at.text_input(key="set_periods").set_value("500").run()  # longer than the bundled data
    run_simulation(at)
    assert at.main.error and len(at.get("plotly_chart")) == 1


def test_email_settings_are_session_only():
    at = start_app()
    at.selectbox(key="page").select("Email Settings").run()
    assert not at.exception
    click(at, "Save")
    assert any("No emails will be sent" in s.value for s in at.sidebar.success)


def test_email_page_shows_last_run_and_settings_survive_page_switch():
    at = start_app()
    at.number_input(key="set_value").set_value(1500).run()
    run_simulation(at)
    assert at.session_state["demo_email_parameters"]["tickers"] == ["AAPL", "NVDA"]
    at.selectbox(key="page").select("Email Settings").run()
    click(at, "Save")
    assert any("AAPL, NVDA" in m.value and "$1500" in m.value for m in at.markdown)

    at.selectbox(key="page").select("Simulator").run()
    assert at.number_input(key="set_value").value == 1500
    assert len(at.get("plotly_chart")) == 4


def test_reset_demo_and_session_isolation():
    first, second = start_app(), start_app()
    assert first.session_state["work_dir"] != second.session_state["work_dir"]

    first.number_input(key="set_value").set_value(3000).run()
    run_simulation(first)
    assert len(first.get("plotly_chart")) == 4
    assert not second.get("plotly_chart")

    old_dir = first.session_state["work_dir"]
    click(first, "Reset demo")
    assert not first.get("plotly_chart")
    assert not os.path.exists(old_dir)
    assert "**$1,000**" in portfolio_line(first)  # defaults are restored


def test_take_a_tour_never_runs_anything():
    at = start_app()
    click(at, "Take a tour")
    assert at.session_state["tour_seen"]
    assert not at.get("plotly_chart")
    assert "results" not in at.session_state
    assert at.number_input(key="set_value").value == 1000


def test_reset_demo_keeps_tour_choice():
    at = start_app()
    click(at, "Take a tour")
    click(at, "Reset demo")
    assert at.session_state["tour_seen"]


def test_app_works_without_tour_package(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "streamlit_tour", None)  # import fails
    monkeypatch.delitem(sys.modules, "demo_tour", raising=False)
    at = start_app()
    click(at, "Take a tour")
    run_simulation(at)
    assert len(at.get("plotly_chart")) == 4


def test_app_works_when_tour_component_fails(monkeypatch):
    import demo_tour

    class BrokenTour:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("tour component failed to initialize")

    monkeypatch.setattr(demo_tour, "Tour", BrokenTour)
    at = start_app()
    assert at.session_state["tour_spotlight_failed"]
    click(at, "Take a tour")
    run_simulation(at)
    assert len(at.get("plotly_chart")) == 4

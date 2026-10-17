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


def test_app_starts_in_demo_mode():
    at = start_app()
    assert any("Demo mode" in i.value for i in at.info)
    assert [t.value for t in at.sidebar.text_input][0] == "AAPL, NVDA"
    assert not at.error


def test_run_simulation_renders_all_strategies():
    at = start_app()
    click(at, "Run Simulation")

    headers = [h.value for h in at.main.header]
    assert headers == ["From 2024-07-10 to 2024-07-18",
                       "Period: 1 Weeks (ending 2024-09-05)",
                       "Period: 4 Weeks (ending 2024-09-05)",
                       "Period: 26 Weeks (ending 2024-09-05)"]
    assert len(at.get("plotly_chart")) == 4
    assert not at.error

    # the summary table compares the three strategies and matches the results committed in the repository
    summary = at.dataframe[0].value
    assert {"always_cash", "always_hold", "dory"} <= set(summary["Advisor"])
    reference = pd.read_csv(os.path.join(APP_DIR, "simulation_results_1.csv"))
    expected_dory = reference[reference["Advisor"] == "dory"].iloc[-1]["Portfolio Value USD"]
    actual_dory = summary[summary["Advisor"] == "dory"].iloc[0]["Final Portfolio Value"]
    assert actual_dory == pytest.approx(expected_dory, abs=1e-3)

    # results stay visible when other inputs change
    at.sidebar.checkbox[0].check().run()
    assert len(at.get("plotly_chart")) == 4


def test_invalid_inputs_show_errors_not_exceptions():
    at = start_app()
    at.sidebar.text_input[0].set_value("AAPL, TSLA").run()
    assert any("TSLA" in e.value for e in at.sidebar.error)
    click(at, "Run Simulation")
    assert not at.get("plotly_chart")

    at = start_app()
    at.sidebar.text_input[1].set_value("1, abc").run()
    click(at, "Run Simulation")
    assert any("whole numbers" in e.value for e in at.sidebar.error)

    at = start_app()
    at.sidebar.text_input[1].set_value("500").run()  # longer than the bundled data
    click(at, "Run Simulation")
    assert at.error and len(at.get("plotly_chart")) == 1


def test_email_settings_are_session_only():
    at = start_app()
    at.sidebar.selectbox[0].select("Email Settings").run()
    assert not at.exception
    click(at, "Save")
    assert any("No emails will be sent" in s.value for s in at.sidebar.success)


def test_email_parameters_are_session_only():
    at = start_app()
    [c for c in at.sidebar.checkbox if c.label == "Update Email Parameters"][0].check().run()
    assert not at.exception
    assert at.session_state["demo_email_parameters"]["tickers"] == ["AAPL", "NVDA"]
    at.sidebar.selectbox[0].select("Email Settings").run()
    click(at, "Save")
    assert any("AAPL, NVDA" in m.value for m in at.markdown)


def test_reset_demo_and_session_isolation():
    first, second = start_app(), start_app()
    assert first.session_state["work_dir"] != second.session_state["work_dir"]

    click(first, "Run Simulation")
    assert len(first.get("plotly_chart")) == 4
    assert not second.get("plotly_chart")

    old_dir = first.session_state["work_dir"]
    click(first, "Reset Demo")
    assert not first.get("plotly_chart")
    assert not os.path.exists(old_dir)


def test_take_a_tour_never_runs_anything():
    at = start_app()
    click(at, "Take a tour")
    assert at.session_state["tour_seen"]
    assert not at.get("plotly_chart")
    assert "results" not in at.session_state


def test_reset_demo_keeps_tour_choice():
    at = start_app()
    click(at, "Take a tour")
    click(at, "Reset Demo")
    assert at.session_state["tour_seen"]


def test_app_works_without_tour_package(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "streamlit_tour", None)  # import fails
    monkeypatch.delitem(sys.modules, "demo_tour", raising=False)
    at = start_app()
    click(at, "Take a tour")
    click(at, "Run Simulation")
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
    click(at, "Run Simulation")
    assert len(at.get("plotly_chart")) == 4

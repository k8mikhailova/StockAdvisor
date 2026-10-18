import hashlib
import importlib
import os
import shutil
import sys
import tempfile
import streamlit as st
from datetime import date, timedelta

# The app's own modules, in dependency order.
LOCAL_MODULES = ["config", "data_fetcher", "advisor_1", "advisor_2", "advisor_3", "simulator", "helper_functions",
                 "ui", "demo_tour"]


def reload_changed_modules():
    """
    A running Streamlit server keeps imported modules in memory. When a deployment pulls new code, this script
    could otherwise run against older versions of its helper modules (for example an AttributeError for a function
    that only exists in the new version). If any module changed on disk since it was loaded, reload all of them in
    dependency order, so they never mix versions.
    """
    app_dir = os.path.dirname(os.path.abspath(__file__))
    digests = {}
    for name in LOCAL_MODULES:
        with open(os.path.join(app_dir, f"{name}.py"), "rb") as file:
            digests[name] = hashlib.sha256(file.read()).hexdigest()
    loaded = [sys.modules.get(name) for name in LOCAL_MODULES]
    if any(module is not None and getattr(module, "_source_digest", None) != digests[name]
           for name, module in zip(LOCAL_MODULES, loaded)):
        for name, module in zip(LOCAL_MODULES, loaded):
            if module is not None:
                importlib.reload(module)
    for name in LOCAL_MODULES:
        module = importlib.import_module(name)
        module._source_digest = digests[name]


reload_changed_modules()

from config import DEFAULT_CALCULATION_TIME, DEFAULT_EMAIL_TIME, DEMO_MODE, HISTORICAL_DATA_PATH
from helper_functions import (validate_tickers, plot_simulation_results, read_and_display, save_email_settings,
                              save_email_parameters, summarize_portfolio)
import pandas as pd
from simulator import get_csv
from data_fetcher import load_historical_data
import demo_tour
import ui

# set page configuration
st.set_page_config(
    page_title="StockAdvisor",  # title of the tab
    page_icon=":bar_chart:"     # icon (can be emoji or path to an image file)
)

# default inputs for demo mode (taken from parameters.json in the repository)
DEMO_TICKERS = "AAPL, NVDA"
DEMO_ALLOCATIONS = {"AAPL": 50, "NVDA": 50, "Cash": 0}
DEMO_SIMULATION_START = date(2024, 7, 10)
DEMO_SIMULATION_END = date(2024, 7, 18)

# session keys of the settings widgets (kept when switching pages, cleared by Reset demo)
SETTING_PREFIXES = ("set_", "alloc_", "adv_")


def get_work_dir():
    """Each visitor gets a private temporary folder for simulation results, so sessions never share files."""
    if 'work_dir' not in st.session_state or not os.path.isdir(st.session_state.work_dir):
        st.session_state.work_dir = tempfile.mkdtemp(prefix="stockadvisor_")
    return st.session_state.work_dir


def reset_demo():
    """Clear this visitor's results and restore the default settings (the tour's "seen" state is kept)."""
    work_dir = st.session_state.get('work_dir')
    if work_dir:
        shutil.rmtree(work_dir, ignore_errors=True)
    for key in list(st.session_state.keys()):
        if not demo_tour.is_tour_key(key):
            del st.session_state[key]


work_dir = get_work_dir()

if DEMO_MODE:
    historical_data = load_historical_data(HISTORICAL_DATA_PATH)
    data_first_date = historical_data['date'].min().date()
    data_last_date = historical_data['date'].max().date()
    data_tickers = sorted(historical_data['ticker'].unique())
    DATA_NOTE = (f":material/history: Demo data: daily {' and '.join(data_tickers)} prices, "
                 f"{ui.format_range(data_first_date, data_last_date)}. Results are simulations on past prices, "
                 f"not live market data or investment advice. No emails are sent.")

# keep the settings when the visitor switches to the Email Settings page and back
for key in list(st.session_state.keys()):
    if key.startswith(SETTING_PREFIXES):
        st.session_state[key] = st.session_state[key]

# default settings (set once per session, so the widgets below don't need a value argument)
defaults = {
    "set_value": 1000,
    "set_tickers": DEMO_TICKERS if DEMO_MODE else "",
    "set_start": data_first_date if DEMO_MODE else date(2023, 1, 1),
    "set_end": data_last_date if DEMO_MODE else date.today(),
    "set_sim_start": DEMO_SIMULATION_START if DEMO_MODE else None,
    "set_sim_end": DEMO_SIMULATION_END if DEMO_MODE else None,
    "set_periods": "1,4,26",
    "set_commission": 0,
    "set_tax": False,
    "set_short_tax": 0,
    "set_long_tax": 0,
    **{f"adv_{advisor}": DEMO_MODE for advisor in ui.ADVISORS},
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)

# creating a dictionary for sidebar navigation
pages = {
    "Simulator": "main",
    "Email Settings": "settings"
}

# sidebar navigation
page = st.sidebar.container(key=demo_tour.PAGES_KEY).selectbox("Page", options=list(pages.keys()), key="page")


if page == "Email Settings":
    st.sidebar.header("Settings")
    st.title("Email Settings")

    if DEMO_MODE:
        st.caption(DATA_NOTE)
        st.write("In the full version, a background script (to_email.py) runs the saved simulation every day and "
                 "emails the charts and summary tables. In this demo, settings are kept only for your visit, the "
                 "report uses your last simulation, and no emails are sent.")

    # create an empty placeholder to display settings
    settings_display_area = st.empty()

    # display current settings
    if DEMO_MODE:
        read_and_display(settings_display_area, st.session_state.get('demo_email_settings', {}),
                         st.session_state.get('demo_email_parameters', {}))
    else:
        read_and_display(settings_display_area)

    # email input
    email = st.sidebar.text_input("Your email", st.session_state.get('email_results', 'you@example.com'))

    # time input for calculations and email
    calculations_time = st.sidebar.time_input("Set up time of day to calculate positions and balances",
                                              st.session_state.get('calculations_time', DEFAULT_CALCULATION_TIME))
    email_time = st.sidebar.time_input("Set up time of day to email results",
                                       st.session_state.get('email_time', DEFAULT_EMAIL_TIME))

    # control Automation
    control_status = st.sidebar.radio("Email Automation",
                                      options=["Active", "Paused"],
                                      index=0 if st.session_state.get('control_status', 'Active') == "Active" else 1)

    # if save button is clicked...
    if st.sidebar.button("Save"):
        # Save settings to session state
        st.session_state.email_results = email
        st.session_state.calculations_time = calculations_time
        st.session_state.email_time = email_time
        st.session_state.control_status = control_status

        if DEMO_MODE:
            # demo mode: keep settings in this session only, never write the shared file or send emails
            st.session_state.demo_email_settings = save_email_settings(email, calculations_time, email_time,
                                                                       control_status, write_file=False)
            st.sidebar.success("Settings saved for this demo session. No emails will be sent.")
            read_and_display(settings_display_area, st.session_state.demo_email_settings,
                             st.session_state.get('demo_email_parameters', {}))
        else:
            # save settings to file
            save_email_settings(email, calculations_time, email_time, control_status)

            # show success message
            st.sidebar.success("Settings saved successfully.")

            # update the display area with the new settings
            read_and_display(settings_display_area)

else:
    # ---------------- sidebar: settings, in the order a visitor fills them in ----------------
    # sections are created first, so the portfolio (which depends on the stock symbols) can sit above them
    portfolio_box = st.sidebar.container(key=demo_tour.PORTFOLIO_KEY)
    data_box = st.sidebar.container(key=demo_tour.INPUTS_KEY)
    simulation_box = st.sidebar.container(key=demo_tour.SIMULATION_KEY)
    advisors_box = st.sidebar.container(key=demo_tour.ADVISORS_KEY)

    # historical data
    data_box.subheader("Historical data")
    tickers = data_box.text_input("Stock symbols (comma-separated)", key="set_tickers",
                                  help=f"Demo data includes: {', '.join(data_tickers)}" if DEMO_MODE else None)

    tickers_list = list(dict.fromkeys(ticker.strip().upper() for ticker in tickers.split(',') if ticker.strip()))
    invalid_tickers = []

    # error handling
    if tickers_list:
        valid_tickers, invalid_tickers = validate_tickers(tickers_list)

        if invalid_tickers:
            if DEMO_MODE:
                data_box.error(f"Not available in the demo data: {', '.join(invalid_tickers)}. "
                               f"Available tickers: {', '.join(data_tickers)}")
            else:
                data_box.error(f"Invalid tickers: {', '.join(invalid_tickers)}")

    # the bundled data covers a fixed date range, so the date pickers are limited to it
    date_limits = dict(min_value=data_first_date, max_value=data_last_date) if DEMO_MODE else {}
    start_col, end_col = data_box.columns(2)
    start_date = start_col.date_input("Data from", key="set_start", **date_limits)
    end_date = end_col.date_input("Data to", key="set_end", **date_limits)
    if DEMO_MODE:
        data_box.caption(f"Available: {ui.format_range(data_first_date, data_last_date)}")

    # simulation settings
    simulation_box.subheader("Simulation settings")
    sim_start_col, sim_end_col = simulation_box.columns(2)
    simulation_start_date = sim_start_col.date_input("Test from", key="set_sim_start", **date_limits)
    simulation_end_date = sim_end_col.date_input("Test to", key="set_sim_end",
                                                 **(date_limits or dict(max_value=date.today())))
    simulation_periods = simulation_box.text_input(
        "Extra test periods (weeks, comma-separated)", key="set_periods",
        help=f"Each number adds a test over the last N weeks of data (ending {ui.format_date(data_last_date)})."
        if DEMO_MODE else "Each number adds a test over the last N weeks, ending today.")

    # portfolio: starting value and allocations, which follow the stock symbols above
    portfolio_box.subheader("Portfolio")
    initial_value = portfolio_box.number_input("Initial portfolio value (USD)", min_value=1, step=100,
                                               key="set_value")
    portfolio_box.caption("Allocations (%)")
    alloc_names = tickers_list + ['Cash']
    alloc_cols = portfolio_box.columns(2)
    for i, name in enumerate(alloc_names):
        st.session_state.setdefault(f"alloc_{name}", DEMO_ALLOCATIONS.get(name, 0) if DEMO_MODE
                                    else (100 if name == 'Cash' else 0))
        alloc_cols[i % 2].number_input(name, min_value=0, max_value=100, step=10, key=f"alloc_{name}")
    allocations = {name: st.session_state[f"alloc_{name}"] for name in alloc_names}
    total_allocation = sum(allocations.values())
    if total_allocation == 100:
        portfolio_box.caption("Total: 100%")
    else:
        portfolio_box.error(f"Allocations add up to {total_allocation}%. They need to total 100%.")

    if DEMO_MODE:
        # commission and tax are not applied by the simulation engine, so the public demo doesn't offer them
        commission_per_trade, include_tax, short_term_capital_gains, long_term_capital_gains = 0, False, 0, 0
    else:
        commission_per_trade = portfolio_box.number_input("Commission per trade", min_value=0, key="set_commission",
                                                          help="Recorded with the simulation parameters. The "
                                                               "simulation engine does not deduct commissions yet.")
        include_tax = portfolio_box.checkbox("Include tax", key="set_tax",
                                             help="Recorded with the simulation parameters. The simulation engine "
                                                  "does not apply taxes yet.")
        short_term_capital_gains = long_term_capital_gains = 0
        if include_tax:
            short_term_capital_gains = portfolio_box.number_input("Short-term capital gains tax rate (%)",
                                                                  min_value=0, key="set_short_tax")
            long_term_capital_gains = portfolio_box.number_input("Long-term capital gains tax rate (%)",
                                                                 min_value=0, key="set_long_tax")

    # advisors
    advisors_box.subheader("Advisors")
    selected_advisors = []
    for advisor, (name, description) in ui.ADVISORS.items():
        if advisors_box.checkbox(name, key=f"adv_{advisor}", help=description):
            selected_advisors.append(advisor)

    def parse_periods():
        try:
            return [int(period.strip()) for period in simulation_periods.split(',') if period.strip()]
        except ValueError:
            return None

    periods = parse_periods()
    if periods is None:
        simulation_box.error("Periods must be whole numbers of weeks, separated by commas.")

    if not DEMO_MODE and st.sidebar.checkbox("Update Email Parameters", key="set_email_parameters"):
        # save parameters for emailing (live mode only; in demo mode the last run is used)
        if periods is not None:
            save_email_parameters(tickers_list, start_date, end_date, simulation_start_date, simulation_end_date,
                                  periods, initial_value, commission_per_trade, include_tax,
                                  short_term_capital_gains, long_term_capital_gains, allocations, selected_advisors)

    # the test windows that one run produces: (tab label, start, end)
    windows = []
    if simulation_start_date and simulation_end_date:
        windows.append((ui.format_range(simulation_start_date, simulation_end_date), simulation_start_date,
                        simulation_end_date))
    # in demo mode the periods end on the last date of the bundled data instead of today
    today = data_last_date if DEMO_MODE else date.today()
    for period in periods or []:
        windows.append((ui.period_label(period), today - timedelta(weeks=period), today))

    current_settings = {"tickers": tuple(tickers_list), "allocations": tuple(allocations.items()),
                        "value": initial_value, "data": (start_date, end_date),
                        "test": (simulation_start_date, simulation_end_date), "periods": simulation_periods,
                        "advisors": tuple(selected_advisors)}

    # ---------------- main area ----------------
    st.title("StockAdvisor")
    st.write("Compare simple investment strategies on historical stock prices. The example below is ready to run, "
             "or change the settings in the sidebar.")
    if DEMO_MODE:
        st.caption(DATA_NOTE)
        tour_slot = st.container()  # welcome card for first-time visitors

    with st.container(key=demo_tour.RUN_KEY):
        st.markdown("#### Your portfolio")
        st.markdown(f"Starting value **${initial_value:,.0f}** · Stocks **{', '.join(tickers_list) or 'none'}** · "
                    f"**{len(selected_advisors)} of {len(ui.ADVISORS)}** strategies selected")
        ui.allocation_bar(allocations)

        st.markdown("#### Compare strategies")
        ui.strategy_overview(selected_advisors)

        # the one simulation action (the button label already names the section)
        run_clicked = st.button("Run simulation", type="primary", icon=":material/play_arrow:", key="run_simulation")
        tests = f"{len(windows)} test{'' if len(windows) == 1 else 's'}"
        st.caption(f"Runs {tests} on the saved historical prices, then shows a chart and summary table for each "
                   f"one below." if DEMO_MODE else f"Runs {tests} with fresh market data, then shows the results "
                                                    f"below.")
        if windows:
            parts = [windows[0][0]] if simulation_start_date and simulation_end_date else []
            if periods:
                weeks = "week" if periods == [1] else "weeks"
                parts.append(f"the last {ui.join_words([str(p) for p in periods])} {weeks} of data "
                             f"(to {ui.format_date(today)})")
            st.caption(f"Test windows: {', plus '.join(parts)}")
        else:
            st.caption("No test windows yet. Set test dates or periods in the sidebar.")

    def run_and_store(window_start, window_end, csv_path, tab_label):
        """Run the simulation for one period and remember the result for this session."""
        # the simulation engine receives the dates as "YYYY-MM-DD" strings, as before
        sim_start, sim_end = window_start.strftime("%Y-%m-%d"), window_end.strftime("%Y-%m-%d")
        try:
            if DEMO_MODE:
                # use the bundled historical data without fetching or modifying it
                get_csv(tickers_list, start_date, end_date, sim_start, sim_end, initial_value, allocations,
                        commission_per_trade, include_tax, short_term_capital_gains, long_term_capital_gains,
                        selected_advisors, csv_path, data_path=HISTORICAL_DATA_PATH, fetch_data=False)
            else:
                # fetch fresh data into this session's folder
                get_csv(tickers_list, start_date, end_date, sim_start, sim_end, initial_value, allocations,
                        commission_per_trade, include_tax, short_term_capital_gains, long_term_capital_gains,
                        selected_advisors, csv_path, data_path=os.path.join(work_dir, "data.csv"), fetch_data=True)
        except (ValueError, RuntimeError, FileNotFoundError) as e:
            st.error(f"{tab_label}: {e}")
            return
        st.session_state.results.append({'advisors': list(selected_advisors), 'csv_path': csv_path,
                                         'tab_label': tab_label, 'date_range': ui.format_range(window_start, window_end)})

    # the simulation action - the existing validation, now shown next to the button
    if run_clicked:
        if invalid_tickers:
            st.error("Please fix the ticker symbols before running the simulation.")
        elif not tickers_list:
            st.error("Please enter at least one stock symbol.")
        elif not selected_advisors:
            st.error("Please select at least one advisor before running the simulation.")
        elif periods is None:
            st.error("Periods must be whole numbers of weeks, separated by commas.")
        elif total_allocation != 100:
            st.error("Total allocations must sum to 100% before running the simulation.")
        elif simulation_start_date and simulation_end_date and not (start_date <= simulation_start_date <= end_date):
            st.error("Simulation start date is out of the historical data range.")
        elif simulation_start_date and simulation_end_date and not (start_date <= simulation_end_date <= end_date):
            st.error("Simulation end date is out of the historical data range.")
        elif simulation_start_date and simulation_end_date and simulation_start_date > simulation_end_date:
            st.error("Simulation start date cannot be after the simulation end date.")
        elif not windows:
            st.error("Please set simulation dates or periods before running the simulation.")
        else:
            st.session_state.results = []
            with st.spinner("Running simulation..."):
                for file_index, (tab_label, sim_start, sim_end) in enumerate(windows, start=1):
                    # overwrite csv file
                    csv_path = os.path.join(work_dir, f"simulation_results_{file_index}.csv")
                    run_and_store(sim_start, sim_end, csv_path, tab_label)
            st.session_state.results_settings = current_settings
            st.session_state.results_summary = (
                f"{', '.join(f'{name} {pct}%' for name, pct in allocations.items())} of "
                f"${initial_value:,.0f}, tested with {', '.join(ui.advisor_name(a) for a in selected_advisors)}.")
            # bring the new results into view (handled by the browser helper below)
            st.session_state.scroll_to_results = st.session_state.get("scroll_to_results", 0) + 1
            st.session_state.scroll_to_results_pending = st.session_state.scroll_to_results
            if DEMO_MODE:
                # the Email Settings page shows the report this run would produce (nothing is saved or sent)
                st.session_state.demo_email_parameters = save_email_parameters(
                    tickers_list, start_date, end_date, simulation_start_date, simulation_end_date, periods or [],
                    initial_value, commission_per_trade, include_tax, short_term_capital_gains,
                    long_term_capital_gains, allocations, selected_advisors, write_file=False)

    # show the latest results of this session (they stay visible while other inputs are changed)
    results = [r for r in st.session_state.get('results', []) if os.path.isfile(r['csv_path'])]
    if results:
        with st.container(key="results_section"):
            st.header("Simulation results")
            st.caption(st.session_state.get("results_summary", ""))
            if st.session_state.get("results_settings") != current_settings:
                st.caption(":material/sync: Your settings have changed since this run. Run the simulation again "
                           "to update these results.")
            # compact comparison: the % return each strategy reached in every test window (from the same summaries
            # shown in the tabs)
            comparison = {}
            for result in results:
                summary = summarize_portfolio(result['csv_path'])
                for _, row in summary[summary['Advisor'].isin(result['advisors'])].iterrows():
                    comparison.setdefault(ui.advisor_name(row['Advisor']), {})[result['tab_label']] = row['% Return']
            comparison_df = pd.DataFrame.from_dict(comparison, orient="index")
            comparison_df = comparison_df.reindex(columns=[r['tab_label'] for r in results])
            comparison_df.index.name = "Strategy"
            st.dataframe(comparison_df.reset_index(), hide_index=True,
                         column_config={col: st.column_config.NumberColumn(format="%.2f%%")
                                        for col in comparison_df.columns})
            st.caption("% return in each test window. Open a tab below for the chart, final values and daily data.")

            with st.container(key=demo_tour.RESULTS_KEY):
                tabs = st.tabs([r['tab_label'] for r in results])
                for tab, result in zip(tabs, results):
                    with tab:
                        st.caption(f"Simulated {result['date_range']}")
                        plot_simulation_results(result['advisors'], result['csv_path'],
                                                period_label=result['tab_label'],
                                                display_names={a: ui.advisor_name(a) for a in ui.ADVISORS},
                                                show_heading=False, colors=ui.strategy_colors())
            st.caption("Change any setting in the sidebar and run the simulation again to compare.")

if DEMO_MODE:
    st.sidebar.divider()
    with st.sidebar.container(horizontal=True):
        if page == "Simulator":
            demo_tour.render_replay_button()
        st.button("Reset demo", on_click=reset_demo, icon=":material/restart_alt:", type="tertiary",
                  help="Clear your results and restore the default settings.")

# small browser helper: tour viewport check, theme for the tour cards, scrolling to new results
with st.sidebar:
    tour_env = demo_tour.mount_env(scroll_to=st.session_state.pop("scroll_to_results_pending", None))
if DEMO_MODE and page == "Simulator":
    with tour_slot:
        demo_tour.render_welcome(tour_env)
    demo_tour.run(tour_env, has_results=bool(st.session_state.get('results')))

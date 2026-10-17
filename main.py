import os
import shutil
import tempfile
import streamlit as st
from datetime import datetime, date, timedelta
from config import DEFAULT_CALCULATION_TIME, DEFAULT_EMAIL_TIME, SETTINGS_FILE_PATH, DEMO_MODE, HISTORICAL_DATA_PATH
from helper_functions import (validate_tickers, plot_simulation_results, read_and_display, save_email_settings,
                              save_email_parameters)
from simulator import get_csv
from data_fetcher import load_historical_data
import demo_tour

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


def get_work_dir():
    """Each visitor gets a private temporary folder for simulation results, so sessions never share files."""
    if 'work_dir' not in st.session_state or not os.path.isdir(st.session_state.work_dir):
        st.session_state.work_dir = tempfile.mkdtemp(prefix="stockadvisor_")
    return st.session_state.work_dir


def reset_demo():
    """Clear this visitor's inputs and results (the tour's "seen" state is kept)."""
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

    st.info(
        f"**Demo mode.** StockAdvisor is running on bundled historical daily prices for "
        f"{', '.join(data_tickers)} from {data_first_date} to {data_last_date}. All results are simulations on past "
        f"data, not live market information or investment advice. No API requests are made and no emails are sent.",
        icon="ℹ️"
    )

    # pre-fill inputs so visitors can run a simulation immediately
    if 'allocations' not in st.session_state:
        st.session_state.allocations = dict(DEMO_ALLOCATIONS)
        st.session_state.saved_allocations = dict(DEMO_ALLOCATIONS)

st.sidebar.header("StockAdvisor Input")

# creating a dictionary for sidebar navigation
pages = {
    "Simulator": "main",
    "Email Settings": "settings"
}

# sidebar navigation
page = st.sidebar.selectbox("Select Page", options=list(pages.keys()))


if page == "Email Settings":
    st.sidebar.header("Settings")
    st.header("Email Settings")

    if DEMO_MODE:
        st.caption("In the full version, a background script (to_email.py) runs the saved simulation every day and "
                   "emails the charts and summary tables. In this demo, settings are kept only for your session and "
                   "no emails are sent.")

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
    # main tab
    if DEMO_MODE:
        tour_slot = st.container()  # welcome card or "Take a tour" button

    st.sidebar.text("")
    inputs_box = st.sidebar.container(key=demo_tour.INPUTS_KEY)
    inputs_box.subheader("Historical Data Input")
    tickers = inputs_box.text_input("Enter Stock Ticker Symbols (comma-separated)",
                                    DEMO_TICKERS if DEMO_MODE else "",
                                    help=f"Demo data includes: {', '.join(data_tickers)}" if DEMO_MODE else None)

    tickers_list = [ticker.strip().upper() for ticker in tickers.split(',') if ticker.strip()]
    invalid_tickers = []

    # error handling
    if tickers_list:
        valid_tickers, invalid_tickers = validate_tickers(tickers_list)

        if invalid_tickers:
            if DEMO_MODE:
                inputs_box.error(f"Not available in the demo data: {', '.join(invalid_tickers)}. "
                                 f"Available tickers: {', '.join(data_tickers)}")
            else:
                inputs_box.error(f"Invalid tickers: {', '.join(invalid_tickers)}")

    if DEMO_MODE:
        # the bundled data covers a fixed date range, so the date pickers are limited to it
        date_limits = dict(min_value=data_first_date, max_value=data_last_date)
        start_date = inputs_box.date_input("Start Date", data_first_date, **date_limits)
        end_date = inputs_box.date_input("End Date", data_last_date, **date_limits)
    else:
        start_date = inputs_box.date_input("Start Date", date(2023, 1, 1))
        end_date = inputs_box.date_input("End Date", date.today())

    inputs_box.text("")
    inputs_box.subheader("Simulation Parameters")
    if DEMO_MODE:
        simulation_start_date = inputs_box.date_input("Simulation Start Date", DEMO_SIMULATION_START, **date_limits)
        simulation_end_date = inputs_box.date_input("Simulation End Date", DEMO_SIMULATION_END, **date_limits)
    else:
        simulation_start_date = inputs_box.date_input("Simulation Start Date", value=None)
        simulation_end_date = inputs_box.date_input("Simulation End Date", value=None, max_value=date.today())
    simulation_periods = inputs_box.text_input(
        "Periods for Simulation (in weeks, comma-separated)", "1,4,26",
        help=f"In demo mode, periods are counted back from {data_last_date}, the last date in the sample data."
        if DEMO_MODE else None)

    initial_value = st.sidebar.number_input("Initial Portfolio Value (USD)", 1000)
    commission_per_trade = st.sidebar.number_input("Commission per Trade", 0,
                                                   help="Recorded with the simulation parameters. The simulation "
                                                        "engine does not deduct commissions yet.")
    # initialize the tax variables with default values
    short_term_capital_gains = 0
    long_term_capital_gains = 0
    include_tax = st.sidebar.checkbox("Include Tax", help="Recorded with the simulation parameters. The simulation "
                                                          "engine does not apply taxes yet.")

    if include_tax:
        short_term_capital_gains = st.sidebar.number_input("Short-term Capital Gains Tax Rate (%)", 0)
        long_term_capital_gains = st.sidebar.number_input("Long-term Capital Gains Tax Rate (%)", 0)

    # collapsible section for portfolio allocations
    with st.sidebar.expander("Portfolio Allocations"):
        if st.button("Update Stocks"):
            st.session_state.allocations = {ticker: 0 for ticker in tickers_list}
            st.session_state.allocations['Cash'] = 100
            st.write("Allocations updated based on input tickers.")

        if 'allocations' in st.session_state:
            st.subheader("Portfolio Allocations")
            st.session_state.allocations['Cash'] = st.number_input("% in Cash", 0, 100, st.session_state.allocations['Cash'], step=10)
            for ticker in st.session_state.allocations:
                if ticker != 'Cash':
                    st.session_state.allocations[ticker] = st.number_input(f"% in {ticker}", 0, 100, st.session_state.allocations[ticker], step=10)

            # ensure allocations sum to 100%
            total_allocation = sum(st.session_state.allocations.values())

            if st.button("Save Allocations"):
                if total_allocation == 100:
                    allocations = {ticker: st.session_state.allocations[ticker] for ticker in st.session_state.allocations}
                    st.session_state.saved_allocations = allocations
                    st.write("Allocations saved.")
                else:
                    st.error("Total allocations must sum to 100% before saving.")

    # advisors selection
    advisors_box = st.sidebar.container(key=demo_tour.ADVISORS_KEY)
    advisors_box.subheader("Advisors")

    advisor_options = {
        "Always Cash": 'always_cash',
        "Always Hold": 'always_hold',
        "Dory": 'dory'
    }

    selected_advisors = []

    for selection, func_name in advisor_options.items():
        if advisors_box.checkbox(selection, DEMO_MODE):
            selected_advisors.append(func_name)

    def parse_periods():
        try:
            return [int(period.strip()) for period in simulation_periods.split(',') if period.strip()]
        except ValueError:
            st.sidebar.error("Periods must be whole numbers of weeks, separated by commas.")
            return None

    st.sidebar.write("")
    if st.sidebar.checkbox("Update Email Parameters"):
        allocations = st.session_state.get('saved_allocations')
        periods = parse_periods()

        if allocations is None:
            st.sidebar.error("Please save allocations first.")
        elif periods is not None:
            # save parameters for emailing (demo mode keeps them in this session only)
            parameters = save_email_parameters(tickers_list, start_date, end_date, simulation_start_date,
                                               simulation_end_date, periods, initial_value, commission_per_trade,
                                               include_tax, short_term_capital_gains, long_term_capital_gains,
                                               allocations, selected_advisors, write_file=not DEMO_MODE)
            if DEMO_MODE:
                st.session_state.demo_email_parameters = parameters

    def run_and_store(sim_start, sim_end, csv_path, period_label):
        """Run the simulation for one period and remember the result for this session."""
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
            st.error(f"{period_label}: {e}")
            return
        st.session_state.results.append({'advisors': list(selected_advisors), 'csv_path': csv_path,
                                         'period_label': period_label})

    # main section - if run simulation button is clicked...
    if st.sidebar.container(key=demo_tour.RUN_KEY).button("Run Simulation"):

        allocations = st.session_state.get('saved_allocations')

        if allocations is None:
            st.sidebar.error("Please update stocks and save new allocations.")
            st.stop()

        # check if allocations match the tickers (this is for error handling)
        allocation_tickers = set(allocations.keys()) - {'Cash'}
        input_tickers = set(tickers_list)
        periods = parse_periods()

        if invalid_tickers:
            st.sidebar.error("Please fix the ticker symbols before running the simulation.")
        elif allocation_tickers != input_tickers:
            st.sidebar.error("Please update stocks and save new allocations.")
        elif not selected_advisors:
            st.sidebar.error("Please select at least one advisor before running the simulation.")
        elif periods is not None and sum(allocations.values()) == 100:
            st.session_state.results = []

            # generate the next csv file name based on the file index
            file_index = 0

            # check if simulation start and end dates are provided
            if simulation_start_date and simulation_end_date:
                # Error handling for simulation start and end dates being out of range
                if not (start_date <= simulation_start_date <= end_date):
                    st.sidebar.error("Simulation start date is out of the historical data range.")
                elif not (start_date <= simulation_end_date <= end_date):
                    st.sidebar.error("Simulation end date is out of the historical data range.")
                elif simulation_start_date > simulation_end_date:
                    st.sidebar.error("Simulation start date cannot be after the simulation end date.")
                else:
                    file_index += 1
                    csv_path = os.path.join(work_dir, f"simulation_results_{file_index}.csv")
                    run_and_store(simulation_start_date, simulation_end_date, csv_path,
                                  f"From {simulation_start_date} to {simulation_end_date}")

            # check if simulation periods are provided
            if periods:
                # in demo mode the periods end on the last date of the bundled data instead of today
                today = data_last_date if DEMO_MODE else date.today()

                for period in periods:
                    file_index += 1
                    period_start_date = today - timedelta(weeks=period)
                    period_end_date = today

                    # convert to strings (e.g., "YYYY-MM-DD")
                    period_start_date_str = period_start_date.strftime("%Y-%m-%d")
                    period_end_date_str = period_end_date.strftime("%Y-%m-%d")

                    # overwrite csv file
                    csv_path = os.path.join(work_dir, f"simulation_results_{file_index}.csv")
                    period_label = f"Period: {period} Weeks"
                    if DEMO_MODE:
                        period_label += f" (ending {period_end_date_str})"
                    run_and_store(period_start_date_str, period_end_date_str, csv_path, period_label)
        else:
            st.sidebar.error("Total allocations must sum to 100% before running the simulation.")

    # show the latest results of this session (they stay visible while other inputs are changed)
    for i, result in enumerate(st.session_state.get('results', [])):
        if os.path.isfile(result['csv_path']):
            with st.container(key=demo_tour.RESULTS_KEY if i == 0 else None):
                plot_simulation_results(result['advisors'], result['csv_path'], period_label=result['period_label'])

if DEMO_MODE:
    st.sidebar.write("")
    st.sidebar.button("Reset Demo", on_click=reset_demo,
                      help="Clear your simulation results, allocations and saved settings. "
                           "Reload the page to also reset every input.")

    # optional onboarding tour (it only explains the interface and never runs anything)
    with st.sidebar:
        tour_env = demo_tour.mount_env()
    if page == "Simulator":
        with tour_slot:
            demo_tour.render_entry(tour_env)
        demo_tour.run(tour_env, has_results=bool(st.session_state.get('results')))

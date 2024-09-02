import streamlit as st
from datetime import datetime, date, timedelta
from config import DEFAULT_CALCULATION_TIME, DEFAULT_EMAIL_TIME, SETTINGS_FILE_PATH
from helper_functions import (validate_tickers, plot_simulation_results, read_and_display, save_email_settings,
                              save_email_parameters)
from simulator import get_csv

# set page configuration
st.set_page_config(
    page_title="StockAdvisor",  # title of the tab
    page_icon=":bar_chart:"     # icon (can be emoji or path to an image file)
)

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

    # create an empty placeholder to display settings
    settings_display_area = st.empty()

    # display current settings
    read_and_display(settings_display_area)

    # email input
    email = st.sidebar.text_input("Your email", st.session_state.get('email_results', 'gordon.janaway@gmail.com'))

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

        # save settings to file
        save_email_settings(email, calculations_time, email_time, control_status)

        # show success message
        st.sidebar.success("Settings saved successfully.")

        # update the display area with the new settings
        read_and_display(settings_display_area)

else:
    # main tab
    st.sidebar.text("")
    st.sidebar.subheader("Historical Data Input")
    tickers = st.sidebar.text_input("Enter Stock Ticker Symbols (comma-separated)")

    # error handling
    if tickers:
        tickers_list = [ticker.strip() for ticker in tickers.split(',')]
        valid_tickers, invalid_tickers = validate_tickers(tickers_list)

        if invalid_tickers:
            st.sidebar.error(f"Invalid tickers: {', '.join(invalid_tickers)}")

    tickers_list = [ticker.strip() for ticker in tickers.split(',')]

    start_date = st.sidebar.date_input("Start Date", date(2023, 1, 1))
    end_date = st.sidebar.date_input("End Date", date.today())

    st.sidebar.text("")
    st.sidebar.subheader("Simulation Parameters")
    simulation_start_date = st.sidebar.date_input("Simulation Start Date", value=None)
    simulation_end_date = st.sidebar.date_input("Simulation End Date", value=None)
    simulation_periods = st.sidebar.text_input("Periods for Simulation (in weeks, comma-separated)", "1,4,26")

    periods = [int(period.strip()) for period in simulation_periods.split(',')]

    initial_value = st.sidebar.number_input("Initial Portfolio Value (USD)", 1000)
    commission_per_trade = st.sidebar.number_input("Commission per Trade", 0)
    # initialize the tax variables with default values
    short_term_capital_gains = 0
    long_term_capital_gains = 0
    include_tax = st.sidebar.checkbox("Include Tax")

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
    st.sidebar.subheader("Advisors")

    advisor_options = {
        "Always Cash": 'always_cash',
        "Always Hold": 'always_hold',
        "Dory": 'dory'
    }

    selected_advisors = []

    for selection, func_name in advisor_options.items():
        if st.sidebar.checkbox(selection, False):
            selected_advisors.append(func_name)

    st.sidebar.write("")
    if st.sidebar.checkbox("Update Email Parameters"):
        allocations = st.session_state.saved_allocations
        # save parameters for emailing
        save_email_parameters(tickers_list, start_date, end_date, simulation_start_date, simulation_end_date, periods,
                              initial_value, commission_per_trade, include_tax, short_term_capital_gains,
                              long_term_capital_gains, allocations, selected_advisors)

    # main section - if run simulation button is clicked...
    if st.sidebar.button("Run Simulation"):

        allocations = st.session_state.saved_allocations

        if not selected_advisors:
            st.sidebar.error("Please select at least one advisor before running the simulation.")
        elif 'saved_allocations' in st.session_state and sum(allocations.values()) == 100:
            # generate the next csv file name based on the file index
            file_index = 0

            # check if simulation start and end dates are provided
            if simulation_start_date and simulation_end_date:
                file_index += 1
                csv_path = f"simulation_results_{file_index}.csv"
                get_csv(tickers_list, start_date, end_date, simulation_start_date, simulation_end_date, initial_value,
                        allocations, commission_per_trade, include_tax, short_term_capital_gains,
                        long_term_capital_gains, selected_advisors, csv_path)
                plot_simulation_results(selected_advisors, csv_path,
                                        period_label=f"From {simulation_start_date} to {simulation_end_date}")
                print(f"Period: {"date input"} CSV file: {csv_path}")

            # check if simulation periods are provided
            if periods:
                today = date.today()

                for period in periods:
                    file_index += 1
                    period_start_date = today - timedelta(weeks=period)
                    period_end_date = today

                    # overwrite csv file
                    csv_path = f"simulation_results_{file_index}.csv"
                    get_csv(tickers_list, start_date, end_date, period_start_date, period_end_date, initial_value,
                            allocations, commission_per_trade, include_tax, short_term_capital_gains,
                            long_term_capital_gains, selected_advisors, csv_path)
                    plot_simulation_results(selected_advisors, csv_path, period_label=f"Period: {period} Weeks")
                    print(f"period: {period} CSV file: {csv_path}")



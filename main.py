import streamlit as st
import datetime
from datetime import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from simulator import get_csv
from config import EMAIL_ADDRESS, DEFAULT_CALCULATION_TIME, DEFAULT_EMAIL_TIME, SETTINGS_FILE_PATH, APP_PASSWORD

# set page configuration
st.set_page_config(
    page_title="Stock Advisor",  # title of the tab
    page_icon=":bar_chart:",     # icon (can be emoji or path to an image file)
    layout="wide"                # layout of the page (optional)
)


# Password protection logic
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        password = st.text_input("Enter the password", type="password")
        if password == APP_PASSWORD:
            st.session_state.password_correct = True
            st.query_params = {"auth": "true"}  # update url to trigger a reload
        elif password:
            st.error("Incorrect password")

    return st.session_state.password_correct


# handle url parameter to reload the page
def handle_url_params():
    query_params = st.query_params
    if query_params.get("auth") == ["true"]:
        st.session_state.password_correct = True


handle_url_params()
# Run the password check
if check_password():
    st.sidebar.header("StockAdvisor")

    # Creating a dictionary for sidebar navigation
    pages = {
        "Main": "main",
        "Settings": "settings"
    }

    # sidebar navigation
    page = st.sidebar.selectbox("Select Page", options=list(pages.keys()))

    if page == "Settings":
        # settings tab
        st.header("Settings")

        # email input
        email = st.sidebar.text_input("Your email", EMAIL_ADDRESS)
        st.session_state.email_results = email

        # time input for calculations and email
        calculations_time = st.sidebar.time_input("Set up time of day to calculate positions and balances", DEFAULT_CALCULATION_TIME)
        st.session_state.calculations_time = calculations_time

        email_time = st.sidebar.time_input("Set up time of day to email results", DEFAULT_EMAIL_TIME)
        st.session_state.email_time = email_time

        # display current settings
        st.write(f"Current Email: {st.session_state.get('email_results', 'Not Set')}")
        st.write(f"Positions and balances will be calculated at {calculations_time.strftime('%I:%M %p')}")
        st.write(f"You will be emailed at {email_time.strftime('%I:%M %p')}")

        # if save button is clicked...
        if st.sidebar.button("Save"):
            # save settings to a file
            with open(SETTINGS_FILE_PATH, "w") as file:
                file.write(f"{st.session_state.email_results}\n")
                file.write(f"{st.session_state.calculations_time.strftime('%H:%M:%S')}\n")
                file.write(f"{st.session_state.email_time.strftime('%H:%M:%S')}\n")

            # show success message
            st.sidebar.success("Settings saved successfully.")

    else:
        # main tab
        st.sidebar.subheader("Historical Data Input")
        tickers = st.sidebar.text_input("Enter Stock Ticker Symbols (comma-separated)")
        start_date = st.sidebar.date_input("Start Date", datetime.date(2023, 1, 1))
        end_date = st.sidebar.date_input("End Date", datetime.date.today())

        st.sidebar.subheader("Simulation Parameters")
        simulation_start_date = st.sidebar.date_input("Simulation Start Date", value=None)
        simulation_end_date = st.sidebar.date_input("Simulation End Date", value=None)
        simulation_periods = st.sidebar.text_input("Periods for Simulation (in weeks, comma-separated)", "1,4,26")
        initial_value = st.sidebar.number_input("Initial Portfolio Value (USD)", 1000)
        commission_per_trade = st.sidebar.number_input("Commission per Trade", 0)
        include_tax = st.sidebar.checkbox("Include Tax")
        short_term_capital_gains = st.sidebar.number_input("Short-term Capital Gains Tax Rate", 0)
        long_term_capital_gains = st.sidebar.number_input("Long-term Capital Gains Tax Rate", 0)

        # collapsible section for portfolio allocations
        with st.sidebar.expander("Portfolio Allocations"):
            if st.button("Update Stocks"):
                tickers_list = [ticker.strip() for ticker in tickers.split(',')]
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

        # main section - if run Simulation button is clicked...
        if st.sidebar.button("Run Simulation"):
            tickers_list = [ticker.strip() for ticker in tickers.split(',')]

            def plot_simulation_results(csv_path, period_label=None):
                # load the csv file into a dataframe and display it
                df = pd.read_csv(csv_path)

                # convert date column to datetime
                df['Date'] = pd.to_datetime(df['Date']).dt.date # convert to date only

                # plot the portfolio value vs time for each advisor
                st.header(f"{period_label if period_label else ''}")
                plt.figure(figsize=(10, 6))

                for advisor in selected_advisors:
                    advisor_df = df[df['Advisor'] == advisor]
                    plt.plot(advisor_df['Date'], advisor_df['Portfolio Value USD'], label=advisor)

                plt.xlabel('Date')
                plt.ylabel('Portfolio Value (USD)')
                plt.title(f'{period_label if period_label else ""}')
                plt.legend()

                # format the date axis to prevent overcrowding
                plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

                # set x-axis limits to start and end dates
                plt.xlim(df['Date'].min(), df['Date'].max())

                # manually set x-axis labels
                date_range = df['Date'].unique()
                step = max(1, len(date_range) // 10)  # adjust step to control the number of labels
                plt.xticks(date_range[::step], rotation=45)

                st.pyplot(plt)

                # display the dataframe as a table
                st.write(df)

            if 'saved_allocations' in st.session_state and sum(st.session_state.saved_allocations.values()) == 100:

                # generate the next csv file name based on the file index
                file_index = 0

                # check if simulation start and end dates are provided
                if simulation_start_date and simulation_end_date:
                    file_index += 1
                    csv_path = f"simulation_results_{file_index}.csv"
                    get_csv(tickers_list, start_date, end_date, simulation_start_date, simulation_end_date, initial_value,
                            st.session_state.saved_allocations, selected_advisors, csv_path)
                    plot_simulation_results(csv_path, period_label=f"From {simulation_start_date} to {simulation_end_date}")
                    st.write(f"CSV file: {csv_path}")

                # check if simulation periods are provided
                if simulation_periods:
                    periods = [int(period.strip()) for period in simulation_periods.split(',')]
                    today = datetime.date.today()

                    for period in periods:
                        file_index += 1
                        period_start_date = today - datetime.timedelta(weeks=period)
                        period_end_date = today

                        # overwrite csv file
                        csv_path = f"simulation_results_{file_index}.csv"
                        get_csv(tickers_list, start_date, end_date, period_start_date, period_end_date, initial_value,
                                st.session_state.saved_allocations, selected_advisors, csv_path)
                        plot_simulation_results(csv_path, period_label=f"Period: {period} Weeks")
                        st.write(f"CSV file: {csv_path}")


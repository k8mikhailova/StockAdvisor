import streamlit as st
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from simulator import get_csv

# Sidebar Inputs
st.sidebar.header("Historical Data Input")
tickers = st.sidebar.text_input("Enter Stock Ticker Symbols (comma-separated)", "AAPL,TSLA")
start_date = st.sidebar.date_input("Start Date", datetime.date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date.today() - datetime.timedelta(days=1))

st.sidebar.header("Simulation Parameters")
simulation_start_date = st.sidebar.date_input("Simulation Start Date", start_date)
simulation_end_date = st.sidebar.date_input("Simulation End Date", end_date)
initial_value = st.sidebar.number_input("Initial Portfolio Value (USD)", 1000)

# Collapsible section for portfolio allocations
with st.sidebar.expander("Portfolio Allocations"):
    if st.button("Update Stocks"):
        tickers_list = [ticker.strip() for ticker in tickers.split(',')]
        st.session_state.allocations = {ticker: 0 for ticker in tickers_list}
        st.session_state.allocations['Cash'] = 100
        st.write("Allocations updated based on input tickers.")

    if 'allocations' in st.session_state:
        st.subheader("Portfolio Allocations")
        st.session_state.allocations['Cash'] = st.number_input("% in Cash", 0, 100, st.session_state.allocations['Cash'])
        for ticker in st.session_state.allocations:
            if ticker != 'Cash':
                st.session_state.allocations[ticker] = st.number_input(f"% in {ticker}", 0, 100, st.session_state.allocations[ticker])

        # Ensure allocations sum to 100%
        total_allocation = sum(st.session_state.allocations.values())
        if total_allocation != 100:
            st.error("Total allocations must sum to 100%.")

        if st.button("Save Allocations"):
            if total_allocation == 100:
                allocations = {ticker: st.session_state.allocations[ticker] for ticker in st.session_state.allocations}
                st.session_state.saved_allocations = allocations
                st.write("Allocations saved.")
            else:
                st.error("Total allocations must sum to 100% before saving.")

# Advisors selection
st.sidebar.header("Advisors")
advisor_options = {
    "Always Cash": 'always_cash',
    "Always Hold": 'always_hold',
    "Dory": 'dory'
}

selected_advisors = []

for selection, func_name in advisor_options.items():
    if st.sidebar.checkbox(selection, True):
        selected_advisors.append(func_name)

# Main section - Run Simulation Button
if st.sidebar.button("Run Simulation"):
    tickers_list = [ticker.strip() for ticker in tickers.split(',')]

    if 'saved_allocations' in st.session_state and sum(st.session_state.saved_allocations.values()) == 100:

        csv_path = get_csv(tickers_list, start_date, end_date, simulation_start_date, simulation_end_date, initial_value, st.session_state.saved_allocations, selected_advisors)

        # Display results
        st.header("Simulation Results")

        # Load the CSV file into a DataFrame and display it
        df = pd.read_csv(csv_path)
        st.write(df)

        # Convert 'Date' column to datetime
        df['Date'] = pd.to_datetime(df['Date'])

        # Plot the portfolio value vs time for each advisor
        st.header("Portfolio Value Over Time")
        plt.figure(figsize=(10, 6))

        for advisor in selected_advisors:
            advisor_df = df[df['Advisor'] == advisor]
            plt.plot(advisor_df['Date'], advisor_df['Portfolio Value USD'], label=advisor)

        plt.xlabel('Date')
        plt.ylabel('Portfolio Value (USD)')
        plt.title('Portfolio Value Over Time')
        plt.legend()

        # Format the date axis to prevent overcrowding
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

        # Manually set x-axis labels
        date_range = df['Date'].unique()
        step = max(1, len(date_range) // 10)  # Adjust step to control the number of labels
        plt.xticks(date_range[::step], rotation=45)

        st.pyplot(plt)


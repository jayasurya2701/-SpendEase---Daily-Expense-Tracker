import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.io as pio

st.set_page_config(page_title="SpendEase - Daily Expense Tracker", page_icon="💸")

# Authentication System
if 'user' not in st.session_state:
    st.session_state.user = None

def login():
    username = st.text_input("Enter Username", key="username")
    password = st.text_input("Enter Password", type="password", key="password")
    if st.button("Login"):
        if username and password:  # Simple check, replace with database auth
            st.session_state.user = username
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid credentials")

def logout():
    st.session_state.user = None
    st.rerun()

if not st.session_state.user:
    st.title("🔒 SpendEase - Secure Expense Tracker")
    login()
    st.stop()

# Tagline
st.sidebar.markdown("### 💰 SpendEase - Track, Save, Succeed!")

# File to store expenses
FILE_PATH = "expenses.csv"
BUDGET_FILE = "budget.txt"

# Load existing expenses from file
try:
    expenses = pd.read_csv(FILE_PATH, parse_dates=['Date'], dayfirst=True)
except FileNotFoundError:
    expenses = pd.DataFrame(columns=['Date', 'Time', 'Period', 'Category', 'Amount'])

# Load or initialize the monthly budget
try:
    with open(BUDGET_FILE, "r") as f:
        monthly_budget = float(f.read().strip())
except (FileNotFoundError, ValueError):
    monthly_budget = 0.0

# Initialize session state
if 'expenses' not in st.session_state:
    st.session_state.expenses = expenses
if 'monthly_budget' not in st.session_state:
    st.session_state.monthly_budget = monthly_budget

st.title("💸 SpendEase - Daily Expense Tracker")

# Expense Entry Section
st.subheader("Enter Your Expenses")
category = st.selectbox("Expense Category", ["Food", "Transport", "Shopping", "Bills", "Others"])
if category == "Others":
    category = st.text_input("Enter Custom Category")
amount = st.number_input("Amount Spent", min_value=0.0, format="%.2f")
date = st.date_input("Date", datetime.date.today())
time = st.time_input("Time", datetime.datetime.now().time()).strftime("%I:%M %p")

# Determine period of the day
hour = datetime.datetime.strptime(time, "%I:%M %p").hour
if 5 <= hour < 12:
    period = "Morning"
elif 12 <= hour < 17:
    period = "Afternoon"
elif 17 <= hour < 21:
    period = "Evening"
else:
    period = "Night"

if st.button("Add Expense"):
    new_expense = pd.DataFrame([[date, time, period, category, amount]], columns=['Date', 'Time', 'Period', 'Category', 'Amount'])
    st.session_state.expenses = pd.concat([st.session_state.expenses, new_expense], ignore_index=True)
    st.session_state.expenses.to_csv(FILE_PATH, index=False)
    st.success("Expense Added!")

# Convert 'Date' column to datetime format
st.session_state.expenses['Date'] = pd.to_datetime(st.session_state.expenses['Date'], errors='coerce', format='%Y-%m-%d')

# Display Daily Total
st.subheader("Today's Total Expense")
today = datetime.date.today()
today_expenses = st.session_state.expenses[st.session_state.expenses['Date'].dt.date == today]
st.metric(label="Total Spent Today", value=f"₹{today_expenses['Amount'].sum():.2f}")

# Sidebar for Weekly & Monthly Summary
st.sidebar.header("Expense Summary")
weekly_expenses = st.session_state.expenses[st.session_state.expenses['Date'] >= pd.to_datetime(today - datetime.timedelta(days=7))]
monthly_expenses = st.session_state.expenses[st.session_state.expenses['Date'].dt.month == today.month]
st.sidebar.subheader("Weekly Total")
st.sidebar.write(f"₹{weekly_expenses['Amount'].sum():.2f}")
st.sidebar.subheader("Monthly Total")
st.sidebar.write(f"₹{monthly_expenses['Amount'].sum():.2f}")

# View past month expenses
st.sidebar.subheader("View Past Expenses")
if not st.session_state.expenses.empty:
    month_options = pd.date_range(start=st.session_state.expenses['Date'].min(), end=today, freq='MS').strftime('%B %Y').unique()
else:
    month_options = []

month_selected = st.sidebar.selectbox("Select Month", month_options)
if month_selected:
    selected_month = datetime.datetime.strptime(month_selected, '%B %Y').month
    past_expenses = st.session_state.expenses[st.session_state.expenses['Date'].dt.month == selected_month]
    st.sidebar.write(f"Total for {month_selected}: ₹{past_expenses['Amount'].sum():.2f}")
    st.sidebar.dataframe(past_expenses)

# Expense Deletion Feature
st.subheader("Manage Expenses")
if not st.session_state.expenses.empty:
    expense_to_delete = st.selectbox("Select an expense to delete", st.session_state.expenses.index)
    if st.button("Delete Selected Expense"):
        st.session_state.expenses = st.session_state.expenses.drop(index=expense_to_delete).reset_index(drop=True)
        st.session_state.expenses.to_csv(FILE_PATH, index=False)
        st.success("Expense Deleted!")

# Visual Analytics
st.subheader("Expense Analytics")
if not st.session_state.expenses.empty:
    category_summary = st.session_state.expenses.groupby('Category')['Amount'].sum().reset_index()
    fig = px.pie(category_summary, names='Category', values='Amount', title='Expense Distribution')
    st.plotly_chart(fig)
    
    # Bar Chart for Expense Trends
    st.subheader("Expense Trends")
    trend_fig = px.bar(st.session_state.expenses, x='Date', y='Amount', color='Category', title='Daily Expense Trends')
    st.plotly_chart(trend_fig)
    
    # Download as PNG
    pio.write_image(fig, "expense_pie_chart.png")
    with open("expense_pie_chart.png", "rb") as file:
        st.download_button("Download Pie Chart as PNG", data=file, file_name="expense_pie_chart.png", mime="image/png")
    
    pio.write_image(trend_fig, "expense_trend_chart.png")
    with open("expense_trend_chart.png", "rb") as file:
        st.download_button("Download Trend Chart as PNG", data=file, file_name="expense_trend_chart.png", mime="image/png")

# Fullscreen Mode Button
if st.button("🔍 Fullscreen Mode"):
    st.write("Press F11 for fullscreen mode on your browser!")

# Budget Setting Feature
st.sidebar.subheader("Set Budget Alert")
st.session_state.monthly_budget = st.sidebar.number_input("Enter Monthly Budget", min_value=0.0, format="%.2f", value=st.session_state.monthly_budget)

# Save the budget to file
with open(BUDGET_FILE, "w") as f:
    f.write(str(st.session_state.monthly_budget))

remaining_budget = st.session_state.monthly_budget - monthly_expenses['Amount'].sum()
st.sidebar.subheader("Remaining Budget")
st.sidebar.write(f"₹{remaining_budget:.2f}")

if remaining_budget < 0:
    st.sidebar.warning("⚠️ You have exceeded your budget!")

# Export Data
st.subheader("Download Expense Report")
st.download_button("Download CSV", data=st.session_state.expenses.to_csv(index=False), file_name="expense_report.csv", mime='text/csv')

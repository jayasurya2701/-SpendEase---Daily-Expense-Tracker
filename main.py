import streamlit as st
import pandas as pd
import datetime
import sqlite3
import hashlib
import plotly.express as px
import plotly.io as pio

st.set_page_config(page_title="SpendEase - Daily Expense Tracker", page_icon="💸")
# Database setup
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")
conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    if result and result[0] == hash_password(password):
        return True
    return False

def register_user(username, password):
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# User authentication
st.sidebar.title("🔑 User Authentication")
menu = st.sidebar.radio("Select an option", ["Login", "Sign Up"])

if menu == "Sign Up":
    st.sidebar.subheader("Create a New Account")
    new_user = st.sidebar.text_input("Username")
    new_password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Register"):
        if register_user(new_user, new_password):
            st.sidebar.success("Account created successfully! Please log in.")
        else:
            st.sidebar.error("Username already taken. Try another one.")

if menu == "Login":
    st.sidebar.subheader("Login to Your Account")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if authenticate(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.sidebar.success("Login successful! Proceed to Expense Tracker.")
        else:
            st.sidebar.error("Invalid credentials. Try again.")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Please log in to access SpendEase.")
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

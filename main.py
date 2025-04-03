import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px

# Set page configuration
st.set_page_config(page_title="SpendEase - Daily Expense Tracker", layout="wide")

# Custom CSS to remove extra padding and center the header
st.markdown(
    """
    <style>
    .block-container { padding-top: 0rem !important; }
    .centered-text {
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        color: #1E88E5;
        margin-top: -50px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Centered Header
st.markdown("<p class='centered-text'>💸 SpendEase - Daily Expense Tracker - Track, Save, Succeed!</p>", unsafe_allow_html=True)

# Connect to SQLite Database
conn = sqlite3.connect("spendease.db", check_same_thread=False)
cursor = conn.cursor()

# Create Tables
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date TEXT,
    time TEXT,
    period TEXT,
    category TEXT,
    amount REAL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS budgets (
    user_id INTEGER PRIMARY KEY,
    budget REAL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')

conn.commit()

# User Authentication Functions
def authenticate(username, password):
    cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    return user[0] if user else None

def register_user(username, password):
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Sidebar Authentication
if "user_id" not in st.session_state:
    st.sidebar.header("🔑 Login / Sign Up")
    auth_option = st.sidebar.radio("Select", ["Login", "Sign Up"])
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if auth_option == "Sign Up":
        if st.sidebar.button("Register"):
            if register_user(username, password):
                st.sidebar.success("✅ Account Created! Please Login.")
            else:
                st.sidebar.error("❌ Username already exists. Try another.")

    if auth_option == "Login":
        if st.sidebar.button("Login"):
            user_id = authenticate(username, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.sidebar.success(f"✅ Welcome {username}!")
                st.rerun()
            else:
                st.sidebar.error("❌ Invalid Credentials!")

    st.stop()

# Get logged-in user ID
user_id = st.session_state.user_id

# Expense Entry Section
st.subheader("📌 Enter Your Expenses")
category = st.selectbox("Expense Category", ["Food", "Transport", "Shopping", "Bills", "Others"])
if category == "Others":
    category = st.text_input("Enter Custom Category")
amount = st.number_input("Amount Spent", min_value=0.0, format="%.2f")
date = st.date_input("Date", datetime.date.today())
time = st.time_input("Time", datetime.datetime.now().time()).strftime("%I:%M %p")

# Determine Time Period
hour = datetime.datetime.strptime(time, "%I:%M %p").hour
period = "Morning" if 5 <= hour < 12 else "Afternoon" if 12 <= hour < 17 else "Evening" if 17 <= hour < 21 else "Night"

if st.button("Add Expense"):
    cursor.execute("INSERT INTO expenses (user_id, date, time, period, category, amount) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, date, time, period, category, amount))
    conn.commit()
    st.success("✅ Expense Added!")
    st.rerun()

# Load Expenses for Logged-in User
expenses = pd.read_sql("SELECT * FROM expenses WHERE user_id=?", conn, params=(user_id,))
expenses["date"] = pd.to_datetime(expenses["date"], errors='coerce')

# Display Daily Total
today = datetime.date.today()
today_expenses = expenses[expenses['date'].dt.date == today]
st.subheader("📊 Today's Total Expense")
st.metric(label="Total Spent Today", value=f"₹{today_expenses['amount'].sum():.2f}")

# Weekly & Monthly Summary
st.sidebar.header("📈 Expense Summary")
weekly_expenses = expenses[expenses["date"] >= pd.to_datetime(today - datetime.timedelta(days=7))]
monthly_expenses = expenses[expenses["date"].dt.month == today.month]

st.sidebar.subheader("📆 Weekly Total")
st.sidebar.write(f"₹{weekly_expenses['amount'].sum():.2f}")

st.sidebar.subheader("📅 Monthly Total")
st.sidebar.write(f"₹{monthly_expenses['amount'].sum():.2f}")

# Budget Setting & Alerts
st.sidebar.subheader("💰 Set Monthly Budget")
cursor.execute("SELECT budget FROM budgets WHERE user_id=?", (user_id,))
budget_data = cursor.fetchone()
current_budget = budget_data[0] if budget_data else 0.0
new_budget = st.sidebar.number_input("Enter Budget", min_value=0.0, format="%.2f", value=current_budget)

if st.sidebar.button("Save Budget"):
    cursor.execute("REPLACE INTO budgets (user_id, budget) VALUES (?, ?)", (user_id, new_budget))
    conn.commit()
    st.sidebar.success("✅ Budget Updated!")
    st.rerun()

remaining_budget = new_budget - monthly_expenses['amount'].sum()
st.sidebar.subheader("📉 Remaining Budget")
st.sidebar.write(f"₹{remaining_budget:.2f}")

if remaining_budget < 0:
    st.sidebar.warning("⚠️ You have exceeded your budget!")

# Expense Deletion
st.subheader("🗑️ Manage Expenses")
if not expenses.empty:
    expense_to_delete = st.selectbox("Select an expense to delete", expenses["id"])
    if st.button("Delete Selected Expense"):
        cursor.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (expense_to_delete, user_id))
        conn.commit()
        st.success("✅ Expense Deleted!")
        st.rerun()

# Expense Visualization
st.subheader("📊 Expense Analytics")
if not expenses.empty:
    category_summary = expenses.groupby('category')['amount'].sum().reset_index()
    fig = px.pie(category_summary, names='category', values='amount', title='Expense Distribution')
    st.plotly_chart(fig)
    
    trend_fig = px.bar(expenses, x='date', y='amount', color='category', title='Daily Expense Trends')
    st.plotly_chart(trend_fig)

# Logout Button
st.sidebar.button("🔒 Logout", on_click=lambda: st.session_state.clear() or st.rerun())

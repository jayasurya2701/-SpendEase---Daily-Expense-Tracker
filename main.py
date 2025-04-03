import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import sqlite3

# Page Configuration
st.set_page_config(page_title="SpendEase - Daily Expense Tracker", page_icon="💸")

# Database Setup
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date TEXT,
    category TEXT,
    amount REAL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS budgets (
    user_id INTEGER PRIMARY KEY,
    monthly_budget REAL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
conn.commit()

# Authentication
if "user_id" not in st.session_state:
    st.session_state.user_id = None

def get_user(username, password):
    cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def create_user(username, email, password):
    try:
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login():
    choice = st.radio("Login or Sign up", ["Login", "Sign up"])
    username = st.text_input("Username")
    email = st.text_input("Email", key="email") if choice == "Sign up" else ""
    password = st.text_input("Password", type="password")
    
    if st.button(choice):
        if choice == "Sign up":
            if create_user(username, email, password):
                st.success("Account created! Please log in.")
            else:
                st.error("Username or Email already exists!")
        else:
            user = get_user(username, password)
            if user:
                st.session_state.user_id = user[0]
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid Credentials")

if not st.session_state.user_id:
    login()
    st.stop()

# Expense Entry Section
st.title("💸 SpendEase - Daily Expense Tracker")
category = st.selectbox("Expense Category", ["Food", "Transport", "Shopping", "Bills", "Others"])
if category == "Others":
    category = st.text_input("Enter Custom Category")
amount = st.number_input("Amount Spent", min_value=0.0, format="%.2f")
date = st.date_input("Date", datetime.date.today())

if st.button("Add Expense"):
    cursor.execute("INSERT INTO expenses (user_id, date, category, amount) VALUES (?, ?, ?, ?)",
                   (st.session_state.user_id, date, category, amount))
    conn.commit()
    st.success("Expense Added!")
    st.rerun()

# Expense Summary
cursor.execute("SELECT date, category, amount FROM expenses WHERE user_id=?", (st.session_state.user_id,))
expenses = pd.DataFrame(cursor.fetchall(), columns=['Date', 'Category', 'Amount'])
expenses['Date'] = pd.to_datetime(expenses['Date'])

st.subheader("Today's Total Expense")
today = datetime.date.today()
today_expenses = expenses[expenses['Date'].dt.date == today]
st.metric(label="Total Spent Today", value=f"₹{today_expenses['Amount'].sum():.2f}")

# Budget Management
st.sidebar.subheader("Set Budget Alert")
cursor.execute("SELECT monthly_budget FROM budgets WHERE user_id=?", (st.session_state.user_id,))
result = cursor.fetchone()
current_budget = result[0] if result else 0.0

new_budget = st.sidebar.number_input("Enter Monthly Budget", min_value=0.0, format="%.2f", value=current_budget)
if st.sidebar.button("Save Budget"):
    cursor.execute("REPLACE INTO budgets (user_id, monthly_budget) VALUES (?, ?)", (st.session_state.user_id, new_budget))
    conn.commit()
    st.success("Budget Updated!")

# Budget Alerts
monthly_expense_total = expenses[expenses['Date'].dt.month == today.month]['Amount'].sum()
remaining_budget = new_budget - monthly_expense_total
st.sidebar.subheader("Remaining Budget")
st.sidebar.write(f"₹{remaining_budget:.2f}")
if remaining_budget < 0:
    st.sidebar.warning("⚠️ You have exceeded your budget!")

# Expense Analytics
st.subheader("Expense Analytics")
if not expenses.empty:
    category_summary = expenses.groupby('Category')['Amount'].sum().reset_index()
    fig = px.pie(category_summary, names='Category', values='Amount', title='Expense Distribution')
    st.plotly_chart(fig)

    trend_fig = px.bar(expenses, x='Date', y='Amount', color='Category', title='Daily Expense Trends')
    st.plotly_chart(trend_fig)

# Download Data
st.subheader("Download Expense Report")
st.download_button("Download CSV", data=expenses.to_csv(index=False), file_name="expense_report.csv", mime='text/csv')

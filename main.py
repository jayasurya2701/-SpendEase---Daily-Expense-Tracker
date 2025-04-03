import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import sqlite3
import smtplib
from email.mime.text import MIMEText

st.set_page_config(page_title="SpendEase - Secure Expense Tracker", page_icon="💸")

# Database setup
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
    time TEXT,
    period TEXT,
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

# User Authentication
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

# Login & Signup
if "user_id" not in st.session_state:
    st.session_state.user_id = None

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
time = st.time_input("Time", datetime.datetime.now().time()).strftime("%I:%M %p")

hour = datetime.datetime.strptime(time, "%I:%M %p").hour
period = "Morning" if 5 <= hour < 12 else "Afternoon" if 12 <= hour < 17 else "Evening" if 17 <= hour < 21 else "Night"

if st.button("Add Expense"):
    cursor.execute("INSERT INTO expenses (user_id, date, time, period, category, amount) VALUES (?, ?, ?, ?, ?, ?)",
                   (st.session_state.user_id, date, time, period, category, amount))
    conn.commit()
    st.success("Expense Added!")

# Fetch expenses for the user
cursor.execute("SELECT date, category, amount FROM expenses WHERE user_id=?", (st.session_state.user_id,))
expenses = pd.DataFrame(cursor.fetchall(), columns=['Date', 'Category', 'Amount'])

st.subheader("Today's Total Expense")
today = datetime.date.today()
today_expenses = expenses[expenses['Date'] == str(today)]
st.metric(label="Total Spent Today", value=f"₹{today_expenses['Amount'].sum():.2f}")

# Budget Feature
st.sidebar.subheader("Set Monthly Budget")
cursor.execute("SELECT monthly_budget FROM budgets WHERE user_id=?", (st.session_state.user_id,))
budget_row = cursor.fetchone()
monthly_budget = budget_row[0] if budget_row else 0.0
monthly_budget = st.sidebar.number_input("Enter Monthly Budget", min_value=0.0, format="%.2f", value=monthly_budget)

if st.sidebar.button("Save Budget"):
    cursor.execute("REPLACE INTO budgets (user_id, monthly_budget) VALUES (?, ?)", (st.session_state.user_id, monthly_budget))
    conn.commit()
    st.success("Budget Saved!")

# Calculate remaining budget
monthly_expense_total = expenses['Amount'].sum()
remaining_budget = monthly_budget - monthly_expense_total
st.sidebar.subheader("Remaining Budget")
st.sidebar.write(f"₹{remaining_budget:.2f}")

if remaining_budget < 0:
    st.sidebar.warning("⚠️ You have exceeded your budget!")
    
    # Email alert
    cursor.execute("SELECT email FROM users WHERE id=?", (st.session_state.user_id,))
    user_email = cursor.fetchone()[0]
    msg = MIMEText(f"You have exceeded your budget! Spent: ₹{monthly_expense_total}, Budget: ₹{monthly_budget}")
    msg["Subject"] = "Budget Exceeded Alert"
    msg["From"] = "your_email@example.com"
    msg["To"] = user_email
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("your_email@example.com", "your_email_password")
            server.sendmail("your_email@example.com", user_email, msg.as_string())
    except Exception as e:
        st.sidebar.error("Failed to send email alert")

# Logout Button
if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.rerun()

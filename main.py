import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import sqlite3
import smtplib
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="SpendEase - Secure Expense Tracker", page_icon="💸")

# Database Setup
def init_db():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT UNIQUE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            date TEXT,
            time TEXT,
            period TEXT,
            category TEXT,
            amount REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            user TEXT PRIMARY KEY,
            budget REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Load authentication config
def load_auth_config():
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Error: '{config_path}' not found. Please ensure the file exists.")
    
    with open(config_path) as file:
        return yaml.load(file, Loader=SafeLoader)

try:
    auth_config = load_auth_config()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()
# Authentication
authenticator = stauth.Authenticate(
    auth_config['credentials'],
    auth_config['cookie']['name'],
    auth_config['cookie']['key'],
    auth_config['cookie']['expiry_days'],
)

name, authentication_status, username = authenticator.login("Login", "main")

if not authentication_status:
    st.warning("Please log in to access SpendEase.")
    st.stop()

st.sidebar.write(f"Logged in as: {username}")
authenticator.logout("Logout", "sidebar")

# Connect to DB
def get_db_connection():
    return sqlite3.connect("expenses.db", check_same_thread=False)

conn = get_db_connection()
cursor = conn.cursor()

# Load user-specific budget
def get_user_budget(user):
    cursor.execute("SELECT budget FROM budgets WHERE user = ?", (user,))
    result = cursor.fetchone()
    return result[0] if result else 0.0

user_budget = get_user_budget(username)
st.session_state.monthly_budget = user_budget

# Expense Entry
st.title("💸 SpendEase - Daily Expense Tracker")
st.subheader("Enter Your Expenses")
category = st.selectbox("Expense Category", ["Food", "Transport", "Shopping", "Bills", "Others"])
if category == "Others":
    category = st.text_input("Enter Custom Category")
amount = st.number_input("Amount Spent", min_value=0.0, format="%.2f")
date = st.date_input("Date", datetime.date.today()).strftime('%Y-%m-%d')
time = st.time_input("Time", datetime.datetime.now().time()).strftime('%H:%M')
period = "Morning" if 5 <= int(time.split(':')[0]) < 12 else "Afternoon" if int(time.split(':')[0]) < 17 else "Evening" if int(time.split(':')[0]) < 21 else "Night"

if st.button("Add Expense"):
    cursor.execute("INSERT INTO expenses (user, date, time, period, category, amount) VALUES (?, ?, ?, ?, ?, ?)",
                   (username, date, time, period, category, amount))
    conn.commit()
    st.success("Expense Added!")

# Load expenses
def load_expenses(user):
    cursor.execute("SELECT * FROM expenses WHERE user = ?", (user,))
    return pd.DataFrame(cursor.fetchall(), columns=['ID', 'User', 'Date', 'Time', 'Period', 'Category', 'Amount'])

expenses = load_expenses(username)

st.subheader("Today's Total Expense")
today = datetime.date.today().strftime('%Y-%m-%d')
today_expenses = expenses[expenses['Date'] == today]
st.metric(label="Total Spent Today", value=f"₹{today_expenses['Amount'].sum():.2f}")

# Budget Setup
st.sidebar.subheader("Set Budget Alert")
new_budget = st.sidebar.number_input("Enter Monthly Budget", min_value=0.0, format="%.2f", value=user_budget)
if st.sidebar.button("Save Budget"):
    cursor.execute("REPLACE INTO budgets (user, budget) VALUES (?, ?)", (username, new_budget))
    conn.commit()
    st.success("Budget Updated!")

remaining_budget = new_budget - expenses['Amount'].sum()
st.sidebar.subheader("Remaining Budget")
st.sidebar.write(f"₹{remaining_budget:.2f}")
if remaining_budget < 0:
    st.sidebar.warning("⚠️ You have exceeded your budget!")
    
    # Send Email Alert
    def send_email_alert(user_email, budget, total_spent):
        sender_email = "your-email@gmail.com"
        sender_password = "your-email-password"
        receiver_email = user_email
        subject = "Budget Alert - SpendEase"
        body = f"Hello,\n\nYou have exceeded your budget of ₹{budget}. Your current total expenditure is ₹{total_spent}.\n\nPlease review your expenses.\n\nBest,\nSpendEase Team"
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            server.quit()
            st.success("Budget alert email sent!")
        except Exception as e:
            st.error(f"Failed to send email: {e}")

    cursor.execute("SELECT email FROM users WHERE username = ?", (username,))
    user_email = cursor.fetchone()[0]
    send_email_alert(user_email, new_budget, expenses['Amount'].sum())

# Close DB Connection
conn.close()

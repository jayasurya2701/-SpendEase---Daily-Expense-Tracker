import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px
import hashlib

DB_FILE = "expenses.db"

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize Database
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
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
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                user_id INTEGER PRIMARY KEY,
                monthly_budget REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

init_db()

# Authentication System
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

def signup():
    username = st.text_input("Create Username")
    password = st.text_input("Create Password", type="password")
    if st.button("Sign Up"):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
                conn.commit()
                st.success("Account created! Please log in.")
            except sqlite3.IntegrityError:
                st.error("Username already exists. Choose another one.")

def login():
    username = st.text_input("Enter Username")
    password = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE username=?", (username,))
            user = cursor.fetchone()
        
        if user and hash_password(password) == user[1]:
            st.session_state.user_id = user[0]
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid credentials")

def logout():
    st.session_state.user_id = None
    st.rerun()

if not st.session_state.user_id:
    st.title("🔒 SpendEase - Secure Expense Tracker")
    option = st.radio("Choose Option", ["Login", "Sign Up"])
    if option == "Login":
        login()
    else:
        signup()
    st.stop()

st.set_page_config(page_title="SpendEase - Daily Expense Tracker", page_icon="💸")
st.sidebar.markdown("### 💰 SpendEase - Track, Save, Succeed!")

# Expense Entry Section
st.title("💸 SpendEase - Daily Expense Tracker")
st.subheader("Enter Your Expenses")
category = st.selectbox("Expense Category", ["Food", "Transport", "Shopping", "Bills", "Others"])
if category == "Others":
    category = st.text_input("Enter Custom Category")
amount = st.number_input("Amount Spent", min_value=0.0, format="%.2f")
date = st.date_input("Date", datetime.date.today())

if st.button("Add Expense") and st.session_state.user_id:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO expenses (user_id, date, category, amount) VALUES (?, ?, ?, ?)",
                       (st.session_state.user_id, date, category, amount))
        conn.commit()
    st.success("Expense Added!")
    st.rerun()

# Fetch Expenses for Current User
expenses_df = pd.DataFrame()
if st.session_state.user_id:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT date, category, amount FROM expenses WHERE user_id=?", (st.session_state.user_id,))
            expenses = cursor.fetchall()
        
        if expenses:
            expenses_df = pd.DataFrame(expenses, columns=["Date", "Category", "Amount"])
            expenses_df["Date"] = pd.to_datetime(expenses_df["Date"])
    except sqlite3.OperationalError as e:
        st.error(f"Database error: {str(e)}")

# Display Today's Expenses
today = datetime.date.today()
today_expenses = expenses_df[expenses_df["Date"].dt.date == today] if not expenses_df.empty else pd.DataFrame()
st.metric(label="Total Spent Today", value=f"₹{today_expenses['Amount'].sum():.2f}" if not today_expenses.empty else "₹0.00")

# Budget Setting
st.sidebar.subheader("Set Monthly Budget")
current_budget = 0.0
if st.session_state.user_id:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT monthly_budget FROM budgets WHERE user_id=?", (st.session_state.user_id,))
        budget_result = cursor.fetchone()
        current_budget = budget_result[0] if budget_result else 0.0

monthly_budget = st.sidebar.number_input("Enter Monthly Budget", min_value=0.0, format="%.2f", value=current_budget)
if st.sidebar.button("Save Budget") and st.session_state.user_id:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if budget_result:
            cursor.execute("UPDATE budgets SET monthly_budget=? WHERE user_id=?", (monthly_budget, st.session_state.user_id))
        else:
            cursor.execute("INSERT INTO budgets (user_id, monthly_budget) VALUES (?, ?)", (st.session_state.user_id, monthly_budget))
        conn.commit()
    st.success("Budget Updated!")

# Expense Visualization
if not expenses_df.empty:
    st.subheader("Expense Analytics")
    category_summary = expenses_df.groupby("Category")["Amount"].sum().reset_index()
    fig = px.pie(category_summary, names="Category", values="Amount", title="Expense Distribution")
    st.plotly_chart(fig)

# Logout Button
if st.sidebar.button("Logout"):
    logout()

import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import matplotlib.pyplot as plt

# Database Connection
def create_connection():
    conn = sqlite3.connect("expenses.db", check_same_thread=False)
    return conn

def create_tables():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY, 
                      username TEXT UNIQUE, 
                      password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
                      id INTEGER PRIMARY KEY, 
                      user TEXT, 
                      category TEXT, 
                      amount REAL, 
                      date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS budgets (
                      user TEXT PRIMARY KEY, 
                      budget REAL)''')
    conn.commit()
    conn.close()

# Password Hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed_password):
    return hash_password(password) == hashed_password

# User Authentication
def register_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user and verify_password(password, user[0])

# Expense Functions
def add_expense(user, category, amount, date):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO expenses (user, category, amount, date) VALUES (?, ?, ?, ?)", (user, category, amount, date))
    conn.commit()
    conn.close()

def get_expenses(user):
    conn = create_connection()
    df = pd.read_sql_query("SELECT category, amount, date FROM expenses WHERE user = ?", conn, params=(user,))
    conn.close()
    return df

# Budget Functions
def set_budget(user, budget):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO budgets (user, budget) VALUES (?, ?)", (user, budget))
    conn.commit()
    conn.close()

def get_budget(user):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT budget FROM budgets WHERE user = ?", (user,))
    budget = cursor.fetchone()
    conn.close()
    return budget[0] if budget else None

# Streamlit UI
st.title("SpendEase - Daily Expense Tracker")
create_tables()

# Authentication Section
menu = ["Login", "Sign Up"]
choice = st.sidebar.selectbox("Menu", menu)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None

if choice == "Sign Up":
    st.subheader("Create an Account")
    new_user = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    if st.button("Sign Up"):
        if register_user(new_user, new_password):
            st.success("Account created! Please log in.")
        else:
            st.error("Username already exists!")

elif choice == "Login":
    st.subheader("Login to Your Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state["logged_in"] = True
            st.session_state["user"] = username
            st.experimental_rerun()
        else:
            st.error("Invalid credentials!")

if st.session_state["logged_in"]:
    st.sidebar.success(f"Logged in as {st.session_state['user']}")
    tab1, tab2, tab3 = st.tabs(["Add Expense", "View Expenses", "Set Budget"])

    with tab1:
        st.subheader("Add New Expense")
        category = st.selectbox("Category", ["Food", "Transport", "Entertainment", "Shopping", "Other"])
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        date = st.date_input("Date")
        if st.button("Add Expense"):
            add_expense(st.session_state["user"], category, amount, date.strftime('%Y-%m-%d'))
            st.success("Expense added successfully!")

    with tab2:
        st.subheader("Expense History")
        df = get_expenses(st.session_state["user"])
        if not df.empty:
            st.dataframe(df)
            st.subheader("Expense Breakdown")
            exp_summary = df.groupby("category")["amount"].sum()
            fig, ax = plt.subplots()
            exp_summary.plot(kind="bar", ax=ax, color="skyblue")
            ax.set_ylabel("Amount Spent")
            st.pyplot(fig)
        else:
            st.info("No expenses recorded yet.")

    with tab3:
        st.subheader("Set Monthly Budget")
        budget = st.number_input("Budget", min_value=0.0, format="%.2f")
        if st.button("Save Budget"):
            set_budget(st.session_state["user"], budget)
            st.success("Budget saved!")

        current_budget = get_budget(st.session_state["user"])
        if current_budget:
            total_spent = df["amount"].sum() if not df.empty else 0
            remaining_budget = current_budget - total_spent
            st.metric("Remaining Budget", f"${remaining_budget:.2f}")
            if remaining_budget < 0:
                st.warning("You have exceeded your budget!")

    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["user"] = None
        st.experimental_rerun()

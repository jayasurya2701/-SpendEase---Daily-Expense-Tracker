import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Database Connection
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

# Ensure Tables Exist
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
        category TEXT,
        amount REAL,
        date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        user_id INTEGER PRIMARY KEY,
        budget REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")
conn.commit()

# Session State
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "budget" not in st.session_state:
    st.session_state.budget = None

# Title
st.sidebar.title("💸 SpendEase - Daily Expense Tracker - Track, Save, Succeed!")

# User Authentication
menu = st.sidebar.radio("🔑 Login / Sign Up", ["Login", "Sign Up"])

if menu == "Sign Up":
    st.subheader("Create an Account")
    new_user = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    if st.button("Sign Up"):
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_user, new_password))
            conn.commit()
            st.success("Account created! Please login.")
        except sqlite3.IntegrityError:
            st.error("Username already exists. Try another one.")

if menu == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            st.session_state.user_id = user[0]
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid credentials.")

# Ensure User is Logged In
if st.session_state.user_id:
    user_id = st.session_state.user_id

    # Budget Tracking
    st.subheader("💰 Set Your Monthly Budget")
    cursor.execute("SELECT budget FROM budgets WHERE user_id = ?", (user_id,))
    budget_row = cursor.fetchone()
    current_budget = budget_row[0] if budget_row else 0
    new_budget = st.number_input("Set Monthly Budget", value=current_budget)
    
    if st.button("Update Budget"):
        if budget_row:
            cursor.execute("UPDATE budgets SET budget = ? WHERE user_id = ?", (new_budget, user_id))
        else:
            cursor.execute("INSERT INTO budgets (user_id, budget) VALUES (?, ?)", (user_id, new_budget))
        conn.commit()
        st.session_state.budget = new_budget
        st.success("Budget updated!")

    # Add Expense
    st.subheader("📝 Add Expense")
    category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"])
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    date = st.date_input("Date")

    if st.button("Add Expense"):
        cursor.execute("INSERT INTO expenses (user_id, category, amount, date) VALUES (?, ?, ?, ?)",
                       (user_id, category, amount, date))
        conn.commit()
        st.success("Expense added!")

    # Show Expenses
    st.subheader("📜 Your Expenses")
    cursor.execute("SELECT id, category, amount, date FROM expenses WHERE user_id = ?", (user_id,))
    expenses = cursor.fetchall()
    
    if expenses:
        df = pd.DataFrame(expenses, columns=["ID", "Category", "Amount", "Date"])
        st.dataframe(df)

        # Budget Alert
        total_spent = df["Amount"].sum()
        if st.session_state.budget and total_spent > st.session_state.budget:
            st.warning("⚠️ You have exceeded your budget!")

        # Graphical Reports
        st.subheader("📊 Expense Insights")
        fig, ax = plt.subplots(1, 2, figsize=(12, 5))

        # Pie Chart
        category_totals = df.groupby("Category")["Amount"].sum()
        ax[0].pie(category_totals, labels=category_totals.index, autopct="%1.1f%%", startangle=90)
        ax[0].set_title("Expense Distribution")

        # Bar Chart
        df["Date"] = pd.to_datetime(df["Date"])
        date_totals = df.groupby("Date")["Amount"].sum()
        ax[1].bar(date_totals.index, date_totals.values)
        ax[1].set_title("Daily Spending")
        ax[1].tick_params(axis="x", rotation=45)

        st.pyplot(fig)

        # Export Data
        st.subheader("📤 Export Data")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="expenses.csv", mime="text/csv")
    else:
        st.info("No expenses found.")

    # Delete Expenses
    st.subheader("🗑️ Delete Expense")
    expense_id = st.number_input("Enter Expense ID to Delete", min_value=1, step=1)
    if st.button("Delete Expense"):
        cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
        conn.commit()
        st.success("Expense deleted!")

else:
    st.warning("Please login to manage your expenses.")

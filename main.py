import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import matplotlib.pyplot as plt

# Set up the Streamlit page
st.set_page_config(page_title="SpendEase - Expense Tracker", layout="wide")

# Custom CSS for center alignment
st.markdown(
    """
    <style>
    .centered-text {
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        color: #1E88E5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Centered Header
st.markdown("<p class='centered-text'>💸 SpendEase - Daily Expense Tracker - Track, Save, Succeed!</p>", unsafe_allow_html=True)

# Connect to database
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables if they don't exist
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

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to check login
def login_user(username, password):
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user and user[1] == hash_password(password):
        return user[0]  # Return user_id
    return None

# Function to register user
def register_user(username, password):
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Sidebar for login/signup
st.sidebar.header("🔑 Login / Sign Up")
auth_option = st.sidebar.radio("Select", ["Login", "Sign Up"])
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

# Login functionality
if auth_option == "Login":
    if st.sidebar.button("Login"):
        user_id = login_user(username, password)
        if user_id:
            st.session_state["logged_in"] = True
            st.session_state["user_id"] = user_id
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid username or password.")

# Signup functionality
elif auth_option == "Sign Up":
    if st.sidebar.button("Sign Up"):
        if register_user(username, password):
            st.success("Account created successfully! Please login.")
        else:
            st.error("Username already exists. Try a different one.")

# Check if user is logged in
if "logged_in" in st.session_state and st.session_state["logged_in"]:
    user_id = st.session_state["user_id"]

    st.subheader("📊 Manage Your Expenses")

    # Fetch user-specific expenses
    cursor.execute("SELECT id, category, amount, date FROM expenses WHERE user_id = ?", (user_id,))
    expenses = cursor.fetchall()

    # Budget Section
    st.write("### 🎯 Set Monthly Budget")
    cursor.execute("SELECT budget FROM budgets WHERE user_id = ?", (user_id,))
    budget_data = cursor.fetchone()
    current_budget = budget_data[0] if budget_data else 0

    new_budget = st.number_input("Enter your monthly budget ($)", min_value=0.0, value=current_budget, step=10.0)

    if st.button("Update Budget"):
        if budget_data:
            cursor.execute("UPDATE budgets SET budget = ? WHERE user_id = ?", (new_budget, user_id))
        else:
            cursor.execute("INSERT INTO budgets (user_id, budget) VALUES (?, ?)", (user_id, new_budget))
        conn.commit()
        st.success("Budget updated!")

    # Calculate total spending
    total_spent = sum(exp[2] for exp in expenses)

    # Show Budget Alert if overspending
    if new_budget > 0 and total_spent > new_budget:
        st.warning(f"⚠️ You have exceeded your budget! Total spent: ${total_spent:.2f} / Budget: ${new_budget:.2f}")

    # Show existing expenses
    if expenses:
        st.write("### Your Expenses:")
        df = pd.DataFrame(expenses, columns=["ID", "Category", "Amount", "Date"])
        st.dataframe(df[["Date", "Category", "Amount"]])

        # Graphical Reports
        st.write("### 📊 Expense Reports")

        # Pie Chart
        category_expenses = df.groupby("Category")["Amount"].sum()
        fig, ax = plt.subplots()
        ax.pie(category_expenses, labels=category_expenses.index, autopct='%1.1f%%', startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

        # Bar Chart
        st.write("### 💰 Spending by Category")
        fig, ax = plt.subplots()
        category_expenses.plot(kind="bar", ax=ax, color="skyblue")
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.write("No expenses recorded yet.")

    # Add a new expense
    st.write("### ➕ Add Expense")
    category = st.selectbox("Category", ["Food", "Transport", "Entertainment", "Bills", "Other"])
    amount = st.number_input("Amount ($)", min_value=0.01, format="%.2f")
    date = st.date_input("Date")

    if st.button("Add Expense"):
        cursor.execute("INSERT INTO expenses (user_id, category, amount, date) VALUES (?, ?, ?, ?)",
                       (user_id, category, amount, str(date)))
        conn.commit()
        st.success("Expense added successfully!")
        st.rerun()

    # Delete expense
    st.write("### ❌ Delete an Expense")
    if expenses:
        delete_expense_id = st.selectbox("Select an expense to delete", [exp[0] for exp in expenses])
        if st.button("Delete"):
            cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (delete_expense_id, user_id))
            conn.commit()
            st.success("Expense deleted successfully!")
            st.rerun()
    else:
        st.write("No expenses to delete.")

    # Export Data as CSV
    st.write("### 📂 Export Expenses")
    if expenses:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv_data, "expenses.csv", "text/csv", key="download-csv")
else:
    st.warning("Please log in to track your expenses.")

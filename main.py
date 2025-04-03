import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import io

# Database Connection
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables if not exist
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
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")
conn.commit()

# Session State for Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None

st.markdown("<h1 style='text-align: center; color: #1E88E5;'>💸 Expense Tracker</h1>", unsafe_allow_html=True)
st.sidebar.header("🔑 Login / Sign Up")

# Authentication Functions
def login(username, password):
    cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    if user:
        st.session_state.authenticated = True
        st.session_state.user_id = user[0]
        return True
    return False

def signup(username, password):
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except:
        return False

# Login / Signup UI
auth_option = st.sidebar.radio("Select", ["Login", "Sign Up"])
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Proceed"):
    if auth_option == "Login":
        if login(username, password):
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid credentials. Try again.")
    else:
        if signup(username, password):
            st.success("Account created! Please login.")
        else:
            st.error("Username already exists!")

# Main Expense Tracker (Only if authenticated)
if st.session_state.authenticated:
    st.header("📊 Expense Tracker")

    # Add Expense
    st.subheader("➕ Add New Expense")
    expense_date = st.date_input("Date")
    category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"])
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    description = st.text_input("Description")

    if st.button("Add Expense"):
        cursor.execute("INSERT INTO expenses (user_id, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
                       (st.session_state.user_id, expense_date, category, amount, description))
        conn.commit()
        st.success("Expense added!")

    # View Expenses
    st.subheader("📜 Expense History")
    cursor.execute("SELECT id, date, category, amount, description FROM expenses WHERE user_id=?", (st.session_state.user_id,))
    data = cursor.fetchall()

    if data:
        df = pd.DataFrame(data, columns=["ID", "Date", "Category", "Amount", "Description"])
        st.dataframe(df)

        # Download CSV
        csv = df.to_csv(index=False).encode()
        st.download_button("⬇ Download CSV", data=csv, file_name="expenses.csv", mime="text/csv")

        # Delete Expense
        delete_id = st.number_input("Enter Expense ID to Delete", min_value=0, step=1)
        if st.button("Delete Expense"):
            cursor.execute("DELETE FROM expenses WHERE id=?", (delete_id,))
            conn.commit()
            st.success("Expense deleted!")
    else:
        st.info("No expenses found.")

    # Visualization
    st.subheader("📈 Expense Analysis")

    # Fetch Data
    cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=? GROUP BY category", (st.session_state.user_id,))
    category_data = cursor.fetchall()
    if category_data:
        df_category = pd.DataFrame(category_data, columns=["Category", "Total Amount"])

        # Pie Chart
        st.subheader("🔹 Category-wise Expense Distribution")
        fig, ax = plt.subplots()
        ax.pie(df_category["Total Amount"], labels=df_category["Category"], autopct="%1.1f%%", startangle=90, colors=sns.color_palette("pastel"))
        ax.axis("equal")
        st.pyplot(fig)

        # Save Chart as PNG
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        st.download_button("📥 Save Pie Chart", buf.getvalue(), file_name="expense_chart.png", mime="image/png")

        # Bar Graph
        st.subheader("🔹 Expense Breakdown by Category")
        fig, ax = plt.subplots()
        sns.barplot(x=df_category["Category"], y=df_category["Total Amount"], palette="viridis", ax=ax)
        ax.set_ylabel("Total Expense")
        ax.set_xlabel("Category")
        st.pyplot(fig)

    else:
        st.info("No expense data available for analysis.")

    # Budget Tracking
    st.subheader("💰 Monthly Budget Tracker")
    budget = st.number_input("Set Your Monthly Budget", min_value=0, step=100)

    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=?", (st.session_state.user_id,))
    total_spent = cursor.fetchone()[0] or 0

    st.write(f"**Total Spent:** ${total_spent:.2f}")
    st.write(f"**Remaining Budget:** ${budget - total_spent:.2f}")

    if total_spent > budget:
        st.warning("⚠ Budget Exceeded!")

    # Logout
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.experimental_rerun()

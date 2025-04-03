import sqlite3
import streamlit as st
import pandas as pd

# Establish connection with SQLite database
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

# Ensure expenses table exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    period TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
conn.commit()

# Streamlit UI
st.title("Expense Tracker")

# Fetch user_id from session state (ensure it's set somewhere in the app)
if "user_id" not in st.session_state:
    st.session_state.user_id = 1  # Default user ID for testing (change as needed)

# Fetch expenses for the user
try:
    cursor.execute("SELECT date, category, amount FROM expenses WHERE user_id=?", (st.session_state.user_id,))
    expenses = cursor.fetchall()
    
    if expenses:
        df = pd.DataFrame(expenses, columns=["Date", "Category", "Amount"])
        st.dataframe(df)
    else:
        st.warning("No expense data found. Start by adding your first expense!")
except sqlite3.OperationalError as e:
    st.error(f"Database error: {str(e)}")
except Exception as e:
    st.error(f"An unexpected error occurred: {str(e)}")

# Close database connection when the app stops
conn.close()

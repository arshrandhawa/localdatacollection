import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, time

# DB setup
def init_db():
    conn = sqlite3.connect("tracking.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            time TEXT,
            started TEXT,
            typetx INTEGER DEFAULT 0,
            typesrp INTEGER DEFAULT 0,
            note TEXT
        );
    """)
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# App UI
st.title("Tracking Entry Form")

names = ["Valkyrie", "Jupyter"]
times = [f"{h}:00 {'AM' if h < 12 else 'PM'}" for h in range(8, 12)] + ["12:00 PM"] + [f"{h-12}:00 PM" for h in range(13, 18)]
type_options = ["Yes", "No"]

with st.form("entry_form"):
    name = st.selectbox("Name", names)
    date = st.date_input("Date", datetime.today())
    time_val = st.selectbox("Time", times)
    type_val = st.selectbox("Started Same Day?", type_options)
    typeTx = st.checkbox("Scheduled Tx")
    typeSRP = st.checkbox("Same Day SRP")
    note = st.text_input("Other Note")
    submitted = st.form_submit_button("Add Entry")

if submitted:
    try:
        cursor.execute("""
            INSERT INTO tracking (name, date, time, started, typetx, typesrp, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, str(date), time_val, type_val, int(typeTx), int(typeSRP), note))
        conn.commit()
        st.success("Entry added!")
    except Exception as e:
        st.error(f"Failed to add entry: {e}")

st.markdown("---")
st.title("View Entries")

df = pd.read_sql_query("SELECT * FROM tracking", conn)
df["date"] = pd.to_datetime(df["date"])

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start date", df["date"].min())
with col2:
    end_date = st.date_input("End date", df["date"].max())

filtered = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]

for _, row in filtered.iterrows():
    with st.expander(f"{row['name']} - {row['date'].date()} - {row['time']}"):
        edit_col, delete_col = st.columns([4, 1])

        with edit_col.form(f"edit_form_{row['id']}"):
            new_name = st.selectbox("Name", names, index=names.index(row["name"]))
            new_date = st.date_input("Date", pd.to_datetime(row["date"]))
            row_time_str = row["time"]
            new_time = st.selectbox("Time", times, index=times.index(row_time_str))
            new_type_val = st.selectbox("Started Same Day?", type_options, index=type_options.index(row["started"]))
            new_typeTx = st.checkbox("Scheduled Tx", value=bool(row["typetx"]))
            new_typeSRP = st.checkbox("Same Day SRP", value=bool(row["typesrp"]))
            new_note = st.text_input("Other Note", value=row["note"])
            update_submit = st.form_submit_button("Update Entry")

        if update_submit:
            try:
                cursor.execute("""
                    UPDATE tracking
                    SET name = ?, date = ?, time = ?, started = ?, typetx = ?, typesrp = ?, note = ?
                    WHERE id = ?
                """, (new_name, str(new_date), new_time, new_type_val, int(new_typeTx), int(new_typeSRP), new_note, row["id"]))
                conn.commit()
                st.success("Entry updated. Refresh to see changes.")
            except Exception as e:
                st.error(f"Failed to update entry: {e}")

        with delete_col:
            if st.button("🗑️ Delete", key=f"delete_{row['id']}"):
                try:
                    cursor.execute("DELETE FROM tracking WHERE id = ?", (row["id"],))
                    conn.commit()
                    st.success("Entry deleted. Refresh to see changes.")
                except Exception as e:
                    st.error(f"Failed to delete entry: {e}")

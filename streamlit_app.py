import streamlit as st
import sqlite3
import pandas as pd
from datetime import time, timedelta

# Setup
st.set_page_config(page_title="Tracking App", layout="wide")

# DB connection
def init_db():
    conn = sqlite3.connect("tracking_v2.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            time TEXT,
            started INTEGER DEFAULT 0,
            typetx INTEGER DEFAULT 0,
            typesrp INTEGER DEFAULT 0,
            note TEXT
        );
    """)
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# Dropdowns
names = ["Valkyrie", "Jupyter"]

def generate_half_hour_slots(start=8, end=17):
    slots = []
    t = datetime.datetime.strptime(f"{start}:00", "%H:%M")
    while t.hour < end or (t.hour == end and t.minute == 0):
        slots.append(t.strftime("%-I:%M %p"))  # e.g., 8:30 AM
        t += datetime.timedelta(minutes=30)
    return slots


times = generate_half_hour_slots()

type_options = ["Yes", "No"]

# Tabs
tab1, tab2, tab3 = st.tabs(["➕ Add Entry", "📄 View Only", "✏️ Manage Entries"])

# --- TAB 1: ADD ENTRY ---
with tab1:
    st.header("➕ Add New Tracking Entry")
    with st.form("entry_form"):
        name = st.selectbox("Name", names)
        date = st.date_input("Date", datetime.today())
        time_val = st.selectbox("Time", times)
        type_val = st.checkbox("Started Same Day?")
        typeTx = st.checkbox("Scheduled Tx")
        typeSRP = st.checkbox("Same Day SRP")
        note = st.text_input("Other Note")
        submitted = st.form_submit_button("Add Entry")

    if submitted:
        try:
            cursor.execute("""
                INSERT INTO tracking (name, date, time, started, typetx, typesrp, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, str(date), time_val, int(type_val), int(typeTx), int(typeSRP), note))
            conn.commit()
            st.success("✅ Entry added!")
        except Exception as e:
            st.error(f"❌ Failed to add entry: {e}")

# --- TAB 2: VIEW ONLY ---
with tab2:
    st.header("📄 All Entries (Read-Only View)")
    df = pd.read_sql_query("SELECT * FROM tracking", conn)
    if df.empty:
        st.info("No data yet.")
    else:
        df["date"] = pd.to_datetime(df["date"])
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", df["date"].min())
        with col2:
            end_date = st.date_input("End Date", df["date"].max())

        filtered = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]
        st.dataframe(filtered.sort_values("date", ascending=False), use_container_width=True)

# --- TAB 3: EDIT / DELETE ---
with tab3:
    st.header("✏️ Manage Entries (Edit / Delete)")
    df = pd.read_sql_query("SELECT * FROM tracking", conn)
    if df.empty:
        st.info("No data yet.")
    else:
        df["date"] = pd.to_datetime(df["date"])
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", df["date"].min(), key="m_start")
        with col2:
            end_date = st.date_input("End Date", df["date"].max(), key="m_end")

        filtered = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]

        for _, row in filtered.iterrows():
            with st.expander(f"{row['name']} — {row['date'].date()} — {row['time']}"):
                edit_col, delete_col = st.columns([4, 1])

                with edit_col.form(f"edit_form_{row['id']}"):
                    new_name = st.selectbox("Name", names, index=names.index(row["name"]))
                    new_date = st.date_input("Date", pd.to_datetime(row["date"]), key=f"d_{row['id']}")
                    new_time = st.selectbox("Time", times, index=times.index(row["time"]))
                    new_type_val = st.checkbox("Started Same Day?", value=bool(row["started"]))
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
                        """, (new_name, str(new_date), new_time, int(new_type_val), int(new_typeTx), int(new_typeSRP), new_note, row["id"]))
                        conn.commit()
                        st.success("✅ Entry updated. Refresh to see changes.")
                    except Exception as e:
                        st.error(f"❌ Failed to update entry: {e}")

                with delete_col:
                    if st.button("🗑️ Delete", key=f"delete_{row['id']}"):
                        try:
                            cursor.execute("DELETE FROM tracking WHERE id = ?", (row["id"],))
                            conn.commit()
                            st.success("🗑️ Entry deleted. Refresh to see changes.")
                        except Exception as e:
                            st.error(f"❌ Failed to delete entry: {e}")

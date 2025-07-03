import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import plotly.express as px

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
names = ["Venus", "Jupiter"]

def generate_half_hour_slots(start=8, end=17):
    slots = []
    t = datetime.strptime(f"{start}:00", "%H:%M")
    while t.hour < end or (t.hour == end and t.minute == 0):
        slots.append(t.strftime("%I:%M %p").lstrip("0"))  # Safer cross-platform
        t += timedelta(minutes=30)
    return slots

times = generate_half_hour_slots()


type_options = ["Yes", "No"]

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Entry", "📄 View Only", "✏️ Manage Entries", "📊 Data Analytics"])

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


with tab4:
    st.header("📊 Checkbox Summary by Person and Overall")

    df = pd.read_sql_query("SELECT * FROM tracking", conn)

    if df.empty:
        st.info("No data available for analysis.")
    else:
        # Preprocess
        df["date"] = pd.to_datetime(df["date"])
        df["started"] = df["started"].astype(bool)
        df["typetx"] = df["typetx"].astype(bool)
        df["typesrp"] = df["typesrp"].astype(bool)

        checkbox_fields = {
            "started": "Started Same Day",
            "typetx": "Scheduled Tx",
            "typesrp": "Same Day SRP"
        }

        # 🔹 Date filter
        st.subheader("📆 Filter Data by Date")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", df["date"].min(), key="filter_start_tab4")
        with col2:
            end_date = st.date_input("End Date", df["date"].max(), key="filter_end_tab4")
            
        df_filtered = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]

        if df_filtered.empty:
            st.warning("No data found for selected date range.")
            st.stop()

        # 🔹 Option to show stats
        show_summary_stats = st.checkbox("📊 Show Summary Stats Table", value=False)

        # 🔹 Per-person breakdown
        st.subheader("👤 Checkbox Rate by Person")

        for name in df_filtered["name"].unique():
            st.markdown(f"### {name}")
            col1, col2, col3 = st.columns(3)

            for i, (field, label) in enumerate(checkbox_fields.items()):
                person_df = df_filtered[df_filtered["name"] == name]
                counts = person_df[field].value_counts().rename({True: "Yes", False: "No"}).reset_index()
                counts.columns = [field, "count"]

                fig = px.pie(
                    counts,
                    names=field,
                    values="count",
                    title=label,
                    hole=0.5,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_traces(
                    textinfo="percent+label",
                    hovertemplate="%{label}<br>Count: %{value}<br>Percent: %{percent}"
                )
                fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))

                [col1, col2, col3][i].plotly_chart(fig, use_container_width=True, key=f"{name}_{field}")

                if show_summary_stats:
                    [col1, col2, col3][i].dataframe(counts, use_container_width=True)

       # 🔹 Overall breakdown (Grouped by person)
        st.subheader("📊 Overall 'Yes' Count by Person per Checkbox")

        col1, col2, col3 = st.columns(3)

        for i, (field, label) in enumerate(checkbox_fields.items()):
            group_yes = (
                df_filtered[df_filtered[field] == True]
                .groupby("name")
                .size()
                .reset_index(name="count")
            )

            if group_yes.empty:
                group_yes = pd.DataFrame({"name": ["No Data"], "count": [1]})

            fig = px.pie(
                group_yes,
                names="name",
                values="count",
                title=label,
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(
                textinfo="percent+label",
                hovertemplate="%{label}<br>Count: %{value}<br>Percent: %{percent}"
            )
            fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))

            [col1, col2, col3][i].plotly_chart(fig, use_container_width=True, key=f"grouped_total_{field}")

            if show_summary_stats:
                [col1, col2, col3][i].dataframe(group_yes, use_container_width=True)


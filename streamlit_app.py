import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from zoneinfo import ZoneInfo
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup
st.set_page_config(page_title="Tracking App", layout="wide")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("TrackingDB").sheet1

# Dropdowns
names = ["Venus", "Jupiter"]

def generate_half_hour_slots(start=8, end=17):
    slots = []
    t = datetime.strptime(f"{start}:00", "%H:%M")
    while t.hour < end or (t.hour == end and t.minute == 0):
        slots.append(t.strftime("%I:%M %p").lstrip("0"))
        t += timedelta(minutes=30)
    return slots

times = generate_half_hour_slots()
mst_now = datetime.now(ZoneInfo("America/Denver"))

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Entry", "📄 View Only", "✏️ Manage Entries", "📊 Data Analytics"])

# --- TAB 1: ADD ENTRY ---
with tab1:
    st.header("➕ Add New Tracking Entry")
    with st.form("entry_form"):
        name = st.selectbox("Name", names)
        date = st.date_input("Date", mst_now.date())
        time_val = st.selectbox("Time", times)
        type_val = st.checkbox("Started Same Day?")
        typeTx = st.checkbox("Scheduled Tx")
        typeSRP = st.checkbox("Same Day SRP")
        note = st.text_input("Other Note")
        submitted = st.form_submit_button("Add Entry")

    if submitted:
        try:
            new_data = [name, str(date), time_val, int(type_val), int(typeTx), int(typeSRP), note]
            sheet.append_row(new_data)
            st.success("✅ Entry added!")
        except Exception as e:
            st.error(f"❌ Failed to add entry: {e}")

# --- TAB 2: VIEW ONLY ---
with tab2:
    st.header("📄 All Entries (Read-Only View)")

    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        st.info("No data yet.")
    else:
        df["date"] = pd.to_datetime(df["date"])
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", df["date"].min(), key="view_start")
        with col2:
            end_date = st.date_input("End Date", df["date"].max(), key="view_end")

        filtered = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]
        st.dataframe(filtered.sort_values("date", ascending=False), use_container_width=True)

# --- TAB 3: Edit / Delete (placeholder only) ---
with tab3:
    st.header("✏️ Manage Entries (Edit / Delete)")
    st.warning("Edit/Delete is disabled for Google Sheets setup. You can manage this directly in the sheet.")

# --- TAB 4: Data Analytics ---
with tab4:
    st.header("📊 Checkbox Summary by Person and Overall")

    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        st.info("No data available for analysis.")
    else:
        df["date"] = pd.to_datetime(df["date"])
        df["started"] = df["started"].astype(bool)
        df["typetx"] = df["typetx"].astype(bool)
        df["typesrp"] = df["typesrp"].astype(bool)

        checkbox_fields = {
            "started": "Started Same Day",
            "typetx": "Scheduled Tx",
            "typesrp": "Same Day SRP"
        }

        # Date filter
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

        show_summary_stats = st.checkbox("📊 Show Summary Stats Table", value=False)

        # Per-person donut charts
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
                fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>Count: %{value}<br>Percent: %{percent}")
                fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))

                [col1, col2, col3][i].plotly_chart(fig, use_container_width=True)

                if show_summary_stats:
                    [col1, col2, col3][i].dataframe(counts, use_container_width=True)

        # Overall donut charts
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
            fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>Count: %{value}<br>Percent: %{percent}")
            fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))

            [col1, col2, col3][i].plotly_chart(fig, use_container_width=True)

            if show_summary_stats:
                [col1, col2, col3][i].dataframe(group_yes, use_container_width=True)

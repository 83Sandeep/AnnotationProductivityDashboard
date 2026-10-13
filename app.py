
import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import date, timedelta

st.set_page_config(
    page_title="Annotation Productivity Dashboard",
    page_icon="📊",
    layout="wide"
)
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False
# -----------------------------
# 1. Generate sample data
# -----------------------------
@st.cache_data
def create_sample_data():
    rows = []
    start_date = date.today() - timedelta(days=13)

    annotators = ["Annotator A", "Annotator B", "Annotator C"]
    types = ["Image", "Video Frame"]

    for day in range(14):
        current_date = start_date + timedelta(days=day)

        for i, annotator in enumerate(annotators):
            completed = 80 + ((day * 13 + i * 17) % 71)
            reviewed = int(completed * 0.8)
            errors = (day + i * 2) % 8
            qc_failed = (day + i) % 5
            qc_passed = reviewed - qc_failed

            rows.append({
                "Date": current_date,
                "Annotator": annotator,
                "Type": types[(day + i) % 2],
                "Completed": completed,
                "Reviewed": reviewed,
                "Errors": errors,
                "QC Passed": qc_passed,
                "QC Failed": qc_failed
            })

    return pd.DataFrame(rows)

df = pd.read_csv("annotation_productivity_sample.csv")
df["Date"] = pd.to_datetime(df["Date"])

# -----------------------------
# 2. Dashboard heading
# -----------------------------
st.title("📊 Data Annotation Productivity")
st.caption(
    "Monitor annotation output, productivity trends "
    "and quality-control results."
)

st.info(
    "Demo dashboard — all records are synthetic sample data."
)

# -----------------------------
# 3. Sidebar filters
# -----------------------------

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filters")

annotator_options = sorted(df["Annotator"].unique())

selected_annotators = st.sidebar.multiselect(
    "Select annotators",
    annotator_options,
    default=annotator_options,
    key="annotator_filter"
)

selected_types = st.sidebar.multiselect(
    "Annotation type",
    sorted(df["Type"].unique()),
    default=sorted(df["Type"].unique()),
    key="type_filter"
)

date_range = st.sidebar.date_input(
    "Date range",
    value=(df["Date"].min().date(),
           df["Date"].max().date()),
    key="date_filter"
)

# Search button below the date range
search_clicked = st.sidebar.button(
    "🔍 Search",
    use_container_width=True
)

if search_clicked:
    st.session_state.search_clicked = True

# Filter only after clicking Search
if not st.session_state.search_clicked:
    st.info("Select your filters and click Search.")
    st.stop()

filtered = df[
    df["Annotator"].isin(selected_annotators)
    & df["Type"].isin(selected_types)
].copy()

if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[
        (filtered["Date"].dt.date >= start)
        & (filtered["Date"].dt.date <= end)
    ]

if filtered.empty:
    st.warning("No data found for these filters.")
    st.stop()

# -----------------------------
# 4. Calculate key metrics
# -----------------------------
total_completed = int(filtered["Completed"].sum())
total_reviewed = int(filtered["Reviewed"].sum())
total_errors = int(filtered["Errors"].sum())

total_passed = int(filtered["QC Passed"].sum())
total_failed = int(filtered["QC Failed"].sum())

total_qc = total_passed + total_failed

error_rate = (
    total_errors / total_reviewed * 100
    if total_reviewed else 0
)

pass_rate = (
    total_passed / total_qc * 100
    if total_qc else 0
)

# -----------------------------
# 5. KPI cards
# -----------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Annotations Completed", f"{total_completed:,}")
c2.metric(
    "Daily Average",
    f"{total_completed / filtered['Date'].nunique():.1f}"
)
c3.metric("Error Rate", f"{error_rate:.2f}%")
c4.metric("QC Pass Rate", f"{pass_rate:.2f}%")

st.divider()

# -----------------------------
# 6. Daily productivity chart
# -----------------------------

# -----------------------------
# 6. Daily Productivity Trend
# -----------------------------
st.subheader("📈 Daily Productivity Trend")

daily = (
    filtered.groupby("Date", as_index=False)
    .agg(
        Completed=("Completed", "sum"),
        Reviewed=("Reviewed", "sum")
    )
    .sort_values("Date")
)

# Calculate the difference between completed and reviewed
daily["Pending Review Estimate"] = (
    daily["Completed"] - daily["Reviewed"]
).clip(lower=0)

# Create comparison chart
fig_daily = px.line(
    daily,
    x="Date",
    y=["Completed", "Reviewed"],
    markers=True,
    title="Completed vs Reviewed Annotations",
    labels={
        "Date": "Date",
        "value": "Number of Annotations",
        "variable": "Activity"
    }
)

fig_daily.update_layout(
    hovermode="x unified",
    legend_title_text="Activity",
    xaxis_title="Date",
    yaxis_title="Number of Annotations"
)

st.plotly_chart(fig_daily, use_container_width=True)

# Show estimated review gap
st.subheader("📋 Review Gap Analysis")

c1, c2, c3 = st.columns(3)

total_completed = int(daily["Completed"].sum())
total_reviewed = int(daily["Reviewed"].sum())
review_gap = int(daily["Pending Review Estimate"].sum())

c1.metric("Completed", f"{total_completed:,}")
c2.metric("Reviewed", f"{total_reviewed:,}")
c3.metric("Estimated Review Gap", f"{review_gap:,}")

st.caption(
    "Review gap = max(completed − reviewed, 0) for each day. "
    "This is an estimate, not a confirmed pending-work count."
)

# -----------------------------
# 7. Annotator comparison
# -----------------------------
left, right = st.columns(2)

with left:
    st.subheader("Output by Annotator")

    by_person = (
        filtered.groupby("Annotator", as_index=False)["Completed"]
        .sum()
        .sort_values("Completed", ascending=False)
    )

    fig_people = px.bar(
        by_person,
        x="Annotator",
        y="Completed",
        color="Annotator",
        title="Total Annotations"
    )

    st.plotly_chart(fig_people, use_container_width=True)

with right:
    st.subheader("Quality Check Results")

    qc = pd.DataFrame({
        "Result": ["Passed", "Failed"],
        "Count": [total_passed, total_failed]
    })

    fig_qc = px.pie(
        qc,
        names="Result",
        values="Count",
        hole=0.45,
        title="QC Pass vs Fail"
    )

    st.plotly_chart(fig_qc, use_container_width=True)

# -----------------------------
# 8. Error analysis
# -----------------------------
st.subheader("Errors by Annotator")

errors_by_person = (
    filtered.groupby("Annotator", as_index=False)["Errors"]
    .sum()
)

fig_errors = px.bar(
    errors_by_person,
    x="Annotator",
    y="Errors",
    color="Errors",
    title="Errors Found During Review"
)

st.plotly_chart(fig_errors, use_container_width=True)

# -----------------------------
# 9. Detailed records
# -----------------------------
st.subheader("Annotation Records")

st.dataframe(
    filtered.sort_values("Date", ascending=False),
    use_container_width=True,
    hide_index=True
)

# -----------------------------
# 10. Download report
# -----------------------------
csv_data = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download CSV Report",
    data=csv_data,
    file_name="annotation_productivity_report.csv",
    mime="text/csv"
)

st.success("Dashboard loaded successfully!")

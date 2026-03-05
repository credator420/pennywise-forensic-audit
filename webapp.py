import streamlit as st
import pandas as pd
import numpy as np
import pennywise as pw
import plotly.graph_objects as go
import pdf_engine

st.set_page_config(page_title="PennyWise", layout="wide")

st.sidebar.title("⚙️ Audit Configuration")

st.sidebar.subheader("📅 Time Scope")

data_filter = st.sidebar.date_input(
    "Select Date Range",
    value=[],
    help="Filter the analysis to a specific period (e.g., Q4 2025)."
)

st.sidebar.subheader("🎚️ Sensitivity Levels")

with st.sidebar.expander("Month-over-Month Logic", expanded=False):
    mom_schock = st.slider(
        "MoM Shock Treshold (%)",
        min_value = 50,
        max_value = 300,
        value = 100,
        help="Flag categories that grow by this percentage over month."
    )
    mom_weight = st.number_input(
        "Minimal Dollar Impact ($)",
        min_value = 500,
        max_value = 2000,
        value = 500,
        help = "Only flag if the raw dollar increase is at least this amount"
    )

with st.sidebar.expander("Oulier Detection (RSF)", expanded=False):
    rsf_treshold = st.slider(
        "RSF Ratio Limit",
        min_value = 2.0,
        max_value = 10.0,
        value = 5.0,
        help="How many times larger the top transaction is compared to the second largest."
    )

st.sidebar.subheader("🛡️ Whitelist")

default_whitelist = ["rent", "payroll", "utilities", "subscription"]

user_whitelist = st.sidebar.multiselect(
    "Ignore Duplicates In:",
    options = default_whitelist + ["marketing", "legal", "taxes", "insurance"],
    default = default_whitelist,
    help = "Transactions in these categories would not be flagged as duplicates."
)

uploaded_file = st.sidebar.file_uploader("Upload Your CSV Data Here", type=["csv"])
risk_treshold = st.sidebar.slider("Risk Sore Treshold", min_value=1, max_value=10, value=5)

st.title("💸 PennyWise: Forensic Dashboard")
st.markdown("### Interactive Audit & Anomaly Detection")

if uploaded_file:
    st.success("Your File Was Uploaded Succesfuly")

    df = pd.read_csv(uploaded_file)

    if len(data_filter) == 2:
        start_date, end_date = data_filter

        df['date'] = pd.to_datetime(df["date"])
        mask = (df['date'].dt.date >= start_date) & ((df['date'].dt.date <= end_date))
        df = df.loc[mask]

        st.info(f"Analysis filtered from {start_date} to {end_date} ({len(df)} rows)")

    with st.spinner("Proccesing Data..."):
        pw.calculate_score(
            df,
            shock_treshold=mom_schock,
            weight_treshold=mom_weight,
            rsf_treshold=rsf_treshold,
            whitelist=user_whitelist
        )
        df = pw.status_labels(df)

    st.success("Audit Completed!")

    high_risk_df = df[df['risk_score'] >= risk_treshold].sort_values(by='risk_score', ascending=False)

    col1, col2 = st.columns(2)
    col1.metric("Total Transactions", len(df))
    col2.metric("High Risk anomalies", len(high_risk_df))

    st.markdown("---")
    st.subheader("🧬 Macro Forensic Analysis: Benford's Law")

    benford_data = pw.benfords_check(df)
    col_chart, col_verdict = st.columns([2, 1])

    with col_chart:

        labels = list(benford_data["expected-counts"].keys())
        expected = list(benford_data["expected-counts"].values())
        actuals = [benford_data["actual-counts"].get(str(i), 0) for i in range(1, 10)]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=actuals, name='Actual Data', marker_color='#3b82f6'))
        fig.add_trace(go.Scatter(x=labels, y=expected, name='Benford Expected', mode='lines+markers', line=dict(color='#ef4444', width=3)))

        fig.update_layout(
            xaxis_title = 'Leading Digit',
            yaxis_title = 'Frequency (%)',
            height = 350,
            margin = dict(l=0, r=30, t=0, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_verdict:

        st.metric("Systemic MAD Score", f"{benford_data['mad-score']:.2f}")

        if benford_data['status-color'] == 'success':
            st.success(benford_data['verdict'])
        elif benford_data['status-color'] == 'warning':
            st.warning(benford_data["verdict"])
        else:
            st.error(benford_data['verdict'])

        for insight in benford_data['insights']:
            st.info(f"💡 **Insight:** {insight}")

    st.markdown('---')

    st.subheader("Critical Findings")
    st.dataframe(
        high_risk_df[['date', 'category', 'description', 'amount', 'risk_score', 'status']],
        use_container_width=True
    )

    pdf_bytes = pdf_engine.generate_executive_pdf(
        mad_score=benford_data['mad-score'],
        verdict=benford_data['verdict'],
        insights=benford_data['insights'],
        fig=fig,
        hit_list_df=high_risk_df
    )

    st.markdown('---')
    colA, colB = st.columns([1, 3])

    with colA:
        st.download_button(
            label='📄 Download Executive PDF',
            data=pdf_bytes,
            file_name='PennyWise_Audit_Report.pdf',
            mime='application/pdf',
            use_container_width=True
        )



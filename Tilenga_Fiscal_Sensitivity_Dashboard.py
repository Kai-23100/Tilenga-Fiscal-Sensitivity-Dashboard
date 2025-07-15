import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import yfinance as yf
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Tilenga Fiscal Sensitivity Dashboard", layout="wide")

# ----------------------
# HEADER
# ----------------------
st.title("Tilenga Project Fiscal Sensitivity Dashboard")
st.markdown("""
This tool allows the Business Development team at TotalEnergies EP Uganda to evaluate the impact of key fiscal variables — such as depreciation rates, royalty thresholds, and oil price volatility — on the cash flow and IRR of the Tilenga Project. It integrates real-world economic data and references Uganda's petroleum legal framework.
""")

# ----------------------
# FETCH REAL ECONOMIC DATA SAFELY
try:
    oil_price_data = yf.download("BZ=F", period="7d", interval="1d")
    latest_oil_price = oil_price_data['Close'].dropna().iloc[-1]
    latest_oil_price = float(latest_oil_price)
except Exception as e:
    st.warning("⚠️ Could not fetch latest oil price. Using fallback value of $75.")
    latest_oil_price = 75.00

# Fetch USD to UGX rate from exchangerate.host
fx_response = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=UGX")
usd_to_ugx = fx_response.json().get('rates', {}).get('UGX', 3800)

# ----------------------
# SIDEBAR - INPUTS
# ----------------------
st.sidebar.header("🔧 Input Assumptions")
oil_price = st.sidebar.number_input("Oil Price ($/bbl)", value=round(latest_oil_price, 2))
production = st.sidebar.number_input("Daily Production (bbl/day)", value=200000)
days_per_year = 365
capex = st.sidebar.number_input("CAPEX (Million $)", value=4000)
opex_per_bbl = st.sidebar.number_input("OPEX per barrel ($)", value=12.0)
depreciation_rate = st.sidebar.selectbox("Depreciation Rate (% per year)", [10, 20, 25, 30])
royalty_rate = st.sidebar.slider("Royalty Rate (%)", 5, 15, 10)
tax_rate = st.sidebar.slider("Corporate Income Tax Rate (%)", 25, 35, 30)
discount_rate = st.sidebar.slider("Discount Rate for NPV (%)", 5, 15, 10)
project_life = st.sidebar.slider("Project Life (Years)", 5, 20, 10)

# ----------------------
# COMPUTATION
# ----------------------
annual_production = production * days_per_year
revenue = oil_price * annual_production / 1e6  # in million $
opex_total = opex_per_bbl * annual_production / 1e6
royalty = revenue * royalty_rate / 100

depreciation = capex * depreciation_rate / 100
profit_before_tax = revenue - opex_total - depreciation - royalty
tax = profit_before_tax * tax_rate / 100
after_tax_profit = profit_before_tax - tax
cash_flow = after_tax_profit + depreciation

# Create projection over project life
years = np.arange(1, project_life + 1)
revenues = np.repeat(revenue, project_life)
opex = np.repeat(opex_total, project_life)
royalties = np.repeat(royalty, project_life)
depreciations = np.repeat(depreciation, project_life)
taxes = np.repeat(tax, project_life)
cash_flows = np.repeat(cash_flow, project_life)

# Discounted Cash Flows
discounted_cash_flows = cash_flows / ((1 + discount_rate / 100) ** years)
npv = npf.npv(discount_rate / 100, [-capex] + list(cash_flows))
irr = npf.irr([-capex] + list(cash_flows)) * 100

# ----------------------
# DASHBOARD DISPLAY
# ----------------------
col1, col2, col3 = st.columns(3)
col1.metric("Project NPV ($M)", f"{npv:,.2f}")
col2.metric("IRR (%)", f"{irr:,.2f}")
col3.metric("Annual Revenue ($M)", f"{revenue:,.2f}")

# Cash Flow Table
st.subheader("Projected Annual Financials")
data = pd.DataFrame({
    "Year": years,
    "Revenue ($M)": revenues,
    "OPEX ($M)": opex,
    "Royalty ($M)": royalties,
    "Depreciation ($M)": depreciations,
    "Tax ($M)": taxes,
    "Net Cash Flow ($M)": cash_flows
})
st.dataframe(data.style.format("{:.2f}"))

# Chart
st.subheader("Net Cash Flow Over Project Life")
st.line_chart(pd.DataFrame({"Year": years, "Net Cash Flow ($M)": cash_flows}).set_index("Year"))

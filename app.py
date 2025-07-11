import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(
    page_title="DCF Model",
    page_icon="💹",
    layout="wide"
)

# --- Helper Functions ---

def format_value(value, value_type="currency"):
    """Formats a number as currency or percentage."""
    if value is None or not isinstance(value, (int, float)):
        return value
    if value_type == "currency":
        return f"${value:,.2f}M"
    elif value_type == "percentage":
        return f"{value:.2%}"
    elif value_type == "multiple":
        return f"{value:.1f}x"
    else:
        return f"{value:,.2f}"

def to_excel(df_dict):
    """Exports a dictionary of DataFrames to an Excel file in memory."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in df_dict.items():
            # Slice multi-index dataframes for clean export
            if isinstance(df.index, pd.MultiIndex):
                df.loc['Income Statement'].to_excel(writer, sheet_name='Income Statement')
                df.loc['Balance Sheet'].to_excel(writer, sheet_name='Balance Sheet')
                df.loc['Cash Flow Statement'].to_excel(writer, sheet_name='Cash Flow Statement')
            else:
                 df.to_excel(writer, sheet_name=sheet_name)
    processed_data = output.getvalue()
    return processed_data

# --- Core Modeling Functions ---

def build_financial_statements(assumptions, historical_data, projection_years_list):
    """Builds the three financial statements based on historicals and assumptions."""
    historical_years = list(historical_data.keys())
    all_years = historical_years + projection_years_list

    # Initialize DataFrame
    idx = pd.MultiIndex.from_tuples([
        ('Income Statement', 'Revenue'), ('Income Statement', 'COGS'), ('Income Statement', 'Gross Profit'),
        ('Income Statement', 'SG&A'), ('Income Statement', 'EBITDA'), ('Income Statement', 'D&A'),
        ('Income Statement', 'EBIT'), ('Income Statement', 'Interest Expense'), ('Income Statement', 'EBT'),
        ('Income Statement', 'Taxes'), ('Income Statement', 'Net Income'),
        ('Balance Sheet', 'Cash & Cash Equivalents'), ('Balance Sheet', 'Accounts Receivable'),
        ('Balance Sheet', 'Inventory'), ('Balance Sheet', 'Total Current Assets'),
        ('Balance Sheet', 'PP&E, Net'), ('Balance Sheet', 'Total Assets'),
        ('Balance Sheet', 'Accounts Payable'), ('Balance Sheet', 'Accrued Liabilities'),
        ('Balance Sheet', 'Total Current Liabilities'), ('Balance Sheet', 'Long-Term Debt'),
        ('Balance Sheet', 'Total Liabilities'), ('Balance Sheet', 'Common Stock'),
        ('Balance Sheet', 'Retained Earnings'), ('Balance Sheet', 'Total Equity'),
        ('Balance Sheet', 'Total Liabilities & Equity'), ('Balance Sheet', 'Balance Check'),
        ('Cash Flow Statement', 'Net Income'), ('Cash Flow Statement', 'D&A'),
        ('Cash Flow Statement', 'Change in Accounts Receivable'), ('Cash Flow Statement', 'Change in Inventory'),
        ('Cash Flow Statement', 'Change in Accounts Payable'), ('Cash Flow Statement', 'Change in Accrued Liabilities'),
        ('Cash Flow Statement', 'Cash Flow from Operations (CFO)'),
        ('Cash Flow Statement', 'Capital Expenditures (Capex)'), ('Cash Flow Statement', 'Cash Flow from Investing (CFI)'),
        ('Cash Flow Statement', 'Debt Issuance / (Repayment)'), ('Cash Flow Statement', 'Cash Flow from Financing (CFF)'),
        ('Cash Flow Statement', 'Net Change in Cash'),
    ])
    model = pd.DataFrame(0.0, index=idx, columns=all_years)

    # Populate Historical Data
    for year in historical_years:
        model.loc[('Income Statement', 'Revenue'), year] = historical_data[year]['Revenue']
        model.loc[('Income Statement', 'COGS'), year] = historical_data[year]['COGS']
        model.loc[('Income Statement', 'SG&A'), year] = historical_data[year]['SG&A']
        model.loc[('Income Statement', 'Interest Expense'), year] = historical_data[year]['Interest Expense']
        model.loc[('Balance Sheet', 'Cash & Cash Equivalents'), year] = historical_data[year]['Cash']
        model.loc[('Balance Sheet', 'Accounts Receivable'), year] = historical_data[year]['Accounts Receivable']
        model.loc[('Balance Sheet', 'Inventory'), year] = historical_data[year]['Inventory']
        model.loc[('Balance Sheet', 'PP&E, Net'), year] = historical_data[year]['PP&E']
        model.loc[('Balance Sheet', 'Accounts Payable'), year] = historical_data[year]['Accounts Payable']
        model.loc[('Balance Sheet', 'Long-Term Debt'), year] = historical_data[year]['Long-Term Debt']
        model.loc[('Balance Sheet', 'Common Stock'), year] = historical_data[year]['Common Stock']
        model.loc[('Balance Sheet', 'Retained Earnings'), year] = historical_data[year]['Retained Earnings']

    # Projection Loop
    for i, year in enumerate(all_years):
        prev_year = all_years[i-1] if i > 0 else None

        # --- Income Statement ---
        if year in projection_years_list:
            model.loc[('Income Statement', 'Revenue'), year] = model.loc[('Income Statement', 'Revenue'), prev_year] * (1 + assumptions['revenue_growth_rate'])

        model.loc[('Income Statement', 'COGS'), year] = model.loc[('Income Statement', 'Revenue'), year] * assumptions['cogs_percent_revenue']
        model.loc[('Income Statement', 'Gross Profit'), year] = model.loc[('Income Statement', 'Revenue'), year] - model.loc[('Income Statement', 'COGS'), year]
        model.loc[('Income Statement', 'SG&A'), year] = model.loc[('Income Statement', 'Revenue'), year] * assumptions['sga_percent_revenue']
        model.loc[('Income Statement', 'EBITDA'), year] = model.loc[('Income Statement', 'Gross Profit'), year] - model.loc[('Income Statement', 'SG&A'), year]

        if prev_year:
            model.loc[('Income Statement', 'D&A'), year] = model.loc[('Balance Sheet', 'PP&E, Net'), prev_year] * assumptions['depreciation_rate']
        else: # Handle first historical year
            model.loc[('Income Statement', 'D&A'), year] = historical_data[year]['D&A']

        model.loc[('Income Statement', 'EBIT'), year] = model.loc[('Income Statement', 'EBITDA'), year] - model.loc[('Income Statement', 'D&A'), year]

        if prev_year:
            model.loc[('Income Statement', 'Interest Expense'), year] = model.loc[('Balance Sheet', 'Long-Term Debt'), prev_year] * assumptions['cost_of_debt']

        model.loc[('Income Statement', 'EBT'), year] = model.loc[('Income Statement', 'EBIT'), year] - model.loc[('Income Statement', 'Interest Expense'), year]
        model.loc[('Income Statement', 'Taxes'), year] = model.loc[('Income Statement', 'EBT'), year] * assumptions['tax_rate']
        model.loc[('Income Statement', 'Net Income'), year] = model.loc[('Income Statement', 'EBT'), year] - model.loc[('Income Statement', 'Taxes'), year]

        # --- Balance Sheet Drivers (Projections only) ---
        if year in projection_years_list:
            model.loc[('Balance Sheet', 'Accounts Receivable'), year] = model.loc[('Income Statement', 'Revenue'), year] * (assumptions['ar_days'] / 365)
            model.loc[('Balance Sheet', 'Inventory'), year] = model.loc[('Income Statement', 'COGS'), year] * (assumptions['inventory_days'] / 365)
            model.loc[('Balance Sheet', 'Accounts Payable'), year] = model.loc[('Income Statement', 'COGS'), year] * (assumptions['ap_days'] / 365)
            model.loc[('Balance Sheet', 'Accrued Liabilities'), year] = model.loc[('Income Statement', 'Revenue'), year] * assumptions['accrued_liabilities_percent_revenue']
        elif year in historical_years: # Use historicals for Accrued Liabilities
             model.loc[('Balance Sheet', 'Accrued Liabilities'), year] = historical_data[year]['Accrued Liabilities']

        # --- Cash Flow Statement (Projections only) ---
        if year in projection_years_list:
            model.loc[('Cash Flow Statement', 'Net Income'), year] = model.loc[('Income Statement', 'Net Income'), year]
            model.loc[('Cash Flow Statement', 'D&A'), year] = model.loc[('Income Statement', 'D&A'), year]
            model.loc[('Cash Flow Statement', 'Change in Accounts Receivable'), year] = model.loc[('Balance Sheet', 'Accounts Receivable'), prev_year] - model.loc[('Balance Sheet', 'Accounts Receivable'), year]
            model.loc[('Cash Flow Statement', 'Change in Inventory'), year] = model.loc[('Balance Sheet', 'Inventory'), prev_year] - model.loc[('Balance Sheet', 'Inventory'), year]
            model.loc[('Cash Flow Statement', 'Change in Accounts Payable'), year] = model.loc[('Balance Sheet', 'Accounts Payable'), year] - model.loc[('Balance Sheet', 'Accounts Payable'), prev_year]
            model.loc[('Cash Flow Statement', 'Change in Accrued Liabilities'), year] = model.loc[('Balance Sheet', 'Accrued Liabilities'), year] - model.loc[('Balance Sheet', 'Accrued Liabilities'), prev_year]

            cfo_rows = [
                ('Cash Flow Statement', 'Net Income'), ('Cash Flow Statement', 'D&A'),
                ('Cash Flow Statement', 'Change in Accounts Receivable'), ('Cash Flow Statement', 'Change in Inventory'),
                ('Cash Flow Statement', 'Change in Accounts Payable'), ('Cash Flow Statement', 'Change in Accrued Liabilities')
            ]
            model.loc[('Cash Flow Statement', 'Cash Flow from Operations (CFO)'), year] = model.loc[cfo_rows, year].sum()

            model.loc[('Cash Flow Statement', 'Capital Expenditures (Capex)'), year] = -(model.loc[('Income Statement', 'Revenue'), year] * assumptions['capex_percent_revenue'])
            model.loc[('Cash Flow Statement', 'Cash Flow from Investing (CFI)'), year] = model.loc[('Cash Flow Statement', 'Capital Expenditures (Capex)'), year]
            repayment = model.loc[('Balance Sheet', 'Long-Term Debt'), prev_year] * assumptions['debt_repayment_percent']
            model.loc[('Cash Flow Statement', 'Debt Issuance / (Repayment)'), year] = -repayment
            model.loc[('Cash Flow Statement', 'Cash Flow from Financing (CFF)'), year] = model.loc[('Cash Flow Statement', 'Debt Issuance / (Repayment)'), year]

            net_cash_change_rows = [
                ('Cash Flow Statement', 'Cash Flow from Operations (CFO)'),
                ('Cash Flow Statement', 'Cash Flow from Investing (CFI)'),
                ('Cash Flow Statement', 'Cash Flow from Financing (CFF)')
            ]
            model.loc[('Cash Flow Statement', 'Net Change in Cash'), year] = model.loc[net_cash_change_rows, year].sum()

        # --- Link CFS to Balance Sheet (Projections only) ---
        if year in projection_years_list:
            model.loc[('Balance Sheet', 'Cash & Cash Equivalents'), year] = model.loc[('Balance Sheet', 'Cash & Cash Equivalents'), prev_year] + model.loc[('Cash Flow Statement', 'Net Change in Cash'), year]
            model.loc[('Balance Sheet', 'PP&E, Net'), year] = model.loc[('Balance Sheet', 'PP&E, Net'), prev_year] + abs(model.loc[('Cash Flow Statement', 'Capital Expenditures (Capex)'), year]) - model.loc[('Income Statement', 'D&A'), year]
            model.loc[('Balance Sheet', 'Long-Term Debt'), year] = model.loc[('Balance Sheet', 'Long-Term Debt'), prev_year] + model.loc[('Cash Flow Statement', 'Debt Issuance / (Repayment)'), year]
            model.loc[('Balance Sheet', 'Retained Earnings'), year] = model.loc[('Balance Sheet', 'Retained Earnings'), prev_year] + model.loc[('Income Statement', 'Net Income'), year]
            model.loc[('Balance Sheet', 'Common Stock'), year] = model.loc[('Balance Sheet', 'Common Stock'), prev_year]

        # --- Final Balance Sheet Calculations (for all years) ---
        tca_rows = [('Balance Sheet', 'Cash & Cash Equivalents'), ('Balance Sheet', 'Accounts Receivable'), ('Balance Sheet', 'Inventory')]
        model.loc[('Balance Sheet', 'Total Current Assets'), year] = model.loc[tca_rows, year].sum()

        model.loc[('Balance Sheet', 'Total Assets'), year] = model.loc[('Balance Sheet', 'Total Current Assets'), year] + model.loc[('Balance Sheet', 'PP&E, Net'), year]

        tcl_rows = [('Balance Sheet', 'Accounts Payable'), ('Balance Sheet', 'Accrued Liabilities')]
        model.loc[('Balance Sheet', 'Total Current Liabilities'), year] = model.loc[tcl_rows, year].sum()

        model.loc[('Balance Sheet', 'Total Liabilities'), year] = model.loc[('Balance Sheet', 'Total Current Liabilities'), year] + model.loc[('Balance Sheet', 'Long-Term Debt'), year]
        model.loc[('Balance Sheet', 'Total Equity'), year] = model.loc[('Balance Sheet', 'Common Stock'), year] + model.loc[('Balance Sheet', 'Retained Earnings'), year]
        model.loc[('Balance Sheet', 'Total Liabilities & Equity'), year] = model.loc[('Balance Sheet', 'Total Liabilities'), year] + model.loc[('Balance Sheet', 'Total Equity'), year]
        model.loc[('Balance Sheet', 'Balance Check'), year] = model.loc[('Balance Sheet', 'Total Assets'), year] - model.loc[('Balance Sheet', 'Total Liabilities & Equity'), year]

    return model

def build_dcf_model(statements, assumptions, projection_years_list):
    """Builds the DCF model."""
    dcf_idx = [
        'EBIT', 'Taxes on EBIT', 'NOPAT', 'D&A', 'Capital Expenditures (Capex)',
        'Change in Net Working Capital', 'Unlevered Free Cash Flow (UFCF)',
        'Discount Factor', 'PV of UFCF'
    ]
    dcf = pd.DataFrame(0.0, index=dcf_idx, columns=projection_years_list)

    # Calculate UFCF
    nwc = (statements.loc[('Balance Sheet', 'Accounts Receivable')] +
           statements.loc[('Balance Sheet', 'Inventory')] -
           statements.loc[('Balance Sheet', 'Accounts Payable')] -
           statements.loc[('Balance Sheet', 'Accrued Liabilities')])
    change_in_nwc = nwc.diff()

    dcf.loc['EBIT'] = statements.loc[('Income Statement', 'EBIT'), projection_years_list]
    dcf.loc['Taxes on EBIT'] = dcf.loc['EBIT'] * assumptions['tax_rate']
    dcf.loc['NOPAT'] = dcf.loc['EBIT'] - dcf.loc['Taxes on EBIT']
    dcf.loc['D&A'] = statements.loc[('Income Statement', 'D&A'), projection_years_list]
    dcf.loc['Capital Expenditures (Capex)'] = statements.loc[('Cash Flow Statement', 'Capital Expenditures (Capex)'), projection_years_list]
    dcf.loc['Change in Net Working Capital'] = -change_in_nwc[projection_years_list]
    dcf.loc['Unlevered Free Cash Flow (UFCF)'] = dcf.loc[['NOPAT', 'D&A', 'Capital Expenditures (Capex)', 'Change in Net Working Capital']].sum(axis=0)

    # Discount UFCF
    discount_periods = np.arange(1, len(projection_years_list) + 1)
    dcf.loc['Discount Factor'] = 1 / (1 + assumptions['wacc']) ** discount_periods
    dcf.loc['PV of UFCF'] = dcf.loc['Unlevered Free Cash Flow (UFCF)'] * dcf.loc['Discount Factor']

    # Terminal Value
    last_proj_year = projection_years_list[-1]
    last_ufcf = dcf.loc['Unlevered Free Cash Flow (UFCF)', last_proj_year]
    terminal_value = (last_ufcf * (1 + assumptions['perpetual_growth_rate'])) / (assumptions['wacc'] - assumptions['perpetual_growth_rate'])
    pv_terminal_value = terminal_value * dcf.loc['Discount Factor', last_proj_year]

    # Enterprise and Equity Value
    enterprise_value = dcf.loc['PV of UFCF'].sum() + pv_terminal_value
    latest_historical_year = str(max([int(y) for y in historical_data.keys()]))
    net_debt = statements.loc[('Balance Sheet', 'Long-Term Debt'), latest_historical_year] - statements.loc[('Balance Sheet', 'Cash & Cash Equivalents'), latest_historical_year]
    equity_value = enterprise_value - net_debt
    implied_share_price = equity_value / assumptions['shares_outstanding'] if assumptions['shares_outstanding'] > 0 else 0

    metrics = {
        'Enterprise Value': enterprise_value, 'Net Debt': net_debt,
        'Equity Value': equity_value, 'Implied Share Price': implied_share_price,
        'Terminal Value': terminal_value, 'PV of Terminal Value': pv_terminal_value,
        'Sum of PV of UFCF': dcf.loc['PV of UFCF'].sum()
    }
    return dcf, metrics

# --- UI & App Layout ---

# NEW: Get Company Name from User
company_name = st.text_input("Enter Company Name", "My Company")

st.title(f"DCF Model: {company_name}")
st.markdown("*An interactive tool for company valuation based on historical data and your assumptions.*")

# --- Sidebar for Inputs ---
st.sidebar.header("Control Panel")

# --- Historical Data Input ---
with st.sidebar.expander("📈 Historical Data Input", expanded=True):
    st.markdown("Enter the last 3 years of financial data (in millions).")

    historical_data = {}
    cols = st.columns(3)
    years = ['2022', '2023', '2024']

    default_data = {
        '2022': {'Revenue': 5000, 'COGS': 2000, 'SG&A': 1000, 'D&A': 500, 'Interest Expense': 150, 'Cash': 500, 'Accounts Receivable': 450, 'Inventory': 600, 'PP&E': 2500, 'Accounts Payable': 250, 'Accrued Liabilities': 150, 'Long-Term Debt': 1500, 'Common Stock': 1000, 'Retained Earnings': 1150},
        '2023': {'Revenue': 5500, 'COGS': 2200, 'SG&A': 1100, 'D&A': 550, 'Interest Expense': 160, 'Cash': 600, 'Accounts Receivable': 500, 'Inventory': 650, 'PP&E': 2800, 'Accounts Payable': 275, 'Accrued Liabilities': 165, 'Long-Term Debt': 1600, 'Common Stock': 1000, 'Retained Earnings': 1500},
        '2024': {'Revenue': 6050, 'COGS': 2420, 'SG&A': 1210, 'D&A': 600, 'Interest Expense': 170, 'Cash': 700, 'Accounts Receivable': 550, 'Inventory': 700, 'PP&E': 3200, 'Accounts Payable': 300, 'Accrued Liabilities': 180, 'Long-Term Debt': 1700, 'Common Stock': 1000, 'Retained Earnings': 1900}
    }

    for i, year in enumerate(years):
        with cols[i]:
            st.subheader(year)
            historical_data[year] = {
                'Revenue': st.number_input(f"Revenue {year}", value=default_data[year]['Revenue'], key=f"rev_{year}"),
                'COGS': st.number_input(f"COGS {year}", value=default_data[year]['COGS'], key=f"cogs_{year}"),
                'SG&A': st.number_input(f"SG&A {year}", value=default_data[year]['SG&A'], key=f"sga_{year}"),
                'D&A': st.number_input(f"D&A {year}", value=default_data[year]['D&A'], key=f"dna_{year}"),
                'Interest Expense': st.number_input(f"Interest Expense {year}", value=default_data[year]['Interest Expense'], key=f"int_{year}"),
                'Cash': st.number_input(f"Cash {year}", value=default_data[year]['Cash'], key=f"cash_{year}"),
                'Accounts Receivable': st.number_input(f"A/R {year}", value=default_data[year]['Accounts Receivable'], key=f"ar_{year}"),
                'Inventory': st.number_input(f"Inventory {year}", value=default_data[year]['Inventory'], key=f"inv_{year}"),
                'PP&E': st.number_input(f"PP&E {year}", value=default_data[year]['PP&E'], key=f"ppe_{year}"),
                'Accounts Payable': st.number_input(f"A/P {year}", value=default_data[year]['Accounts Payable'], key=f"ap_{year}"),
                'Accrued Liabilities': st.number_input(f"Accrued Liab. {year}", value=default_data[year]['Accrued Liabilities'], key=f"al_{year}"),
                'Long-Term Debt': st.number_input(f"L/T Debt {year}", value=default_data[year]['Long-Term Debt'], key=f"ltd_{year}"),
                'Common Stock': st.number_input(f"Common Stock {year}", value=default_data[year]['Common Stock'], key=f"cs_{year}"),
                'Retained Earnings': st.number_input(f"Retained Earnings {year}", value=default_data[year]['Retained Earnings'], key=f"re_{year}"),
            }

# --- Calculated Historical Assumptions ---
try:
    cagr = (historical_data['2024']['Revenue'] / historical_data['2022']['Revenue']) ** (1/2) - 1
    cogs_percent_avg = np.mean([historical_data[y]['COGS'] / historical_data[y]['Revenue'] for y in years])
    sga_percent_avg = np.mean([historical_data[y]['SG&A'] / historical_data[y]['Revenue'] for y in years])
except ZeroDivisionError:
    cagr, cogs_percent_avg, sga_percent_avg = 0.0, 0.0, 0.0

# --- Operational Assumptions ---
with st.sidebar.expander("⚙️ Operational Assumptions"):
    st.markdown("**Growth & Profitability**")
    rev_growth_override = st.slider("Revenue Growth Rate (%)", 0.0, 25.0, cagr * 100, 0.5, help="Override the historically calculated CAGR.") / 100
    cogs_percent_override = st.slider("COGS (% of Revenue)", 0.0, 100.0, cogs_percent_avg * 100, 1.0, help="Override the historical average.") / 100
    sga_percent_override = st.slider("SG&A (% of Revenue)", 0.0, 100.0, sga_percent_avg * 100, 1.0, help="Override the historical average.") / 100

    st.markdown("**Balance Sheet & Cash Flow**")
    ar_days = st.slider("A/R Days", 0, 90, 30)
    inventory_days = st.slider("Inventory Days", 0, 90, 45)
    ap_days = st.slider("A/P Days", 0, 90, 25)
    accrued_liabilities_percent_revenue = st.slider("Accrued Liabilities (% of Revenue)", 0.0, 10.0, 3.0, 0.1) / 100
    depreciation_rate = st.slider("Depreciation (% of prior PP&E)", 0.0, 25.0, 10.0, 0.5) / 100
    capex_percent_revenue = st.slider("Capex (% of Revenue)", 0.0, 25.0, 12.0, 0.5) / 100
    debt_repayment_percent = st.slider("Annual Debt Repayment (%)", 0.0, 10.0, 2.0, 0.5) / 100

    st.markdown("**General**")
    tax_rate = st.slider("Corporate Tax Rate (%)", 0.0, 50.0, 21.0, 1.0) / 100
    shares_outstanding = st.number_input("Shares Outstanding (in millions)", value=500.0)

# --- WACC Inputs ---
with st.sidebar.expander("⚖️ WACC Inputs"):
    risk_free_rate = st.slider("Risk-Free Rate (%)", 0.0, 10.0, 4.5, 0.1, help="Typically the yield on a 10-year government bond.") / 100
    market_risk_premium = st.slider("Market Risk Premium (%)", 0.0, 15.0, 5.5, 0.1, help="The excess return that investing in the stock market provides over the risk-free rate.") / 100
    company_beta = st.slider("Company Beta", 0.0, 3.0, 1.2, 0.1, help="A measure of the stock's volatility in relation to the overall market.")
    market_cap = st.number_input("Market Cap (in millions)", value=10000.0, help="Market Value of Equity.")

    cost_of_equity = risk_free_rate + company_beta * market_risk_premium
    try:
        cost_of_debt = historical_data['2024']['Interest Expense'] / historical_data['2024']['Long-Term Debt']
    except ZeroDivisionError:
        cost_of_debt = 0.03

    market_value_of_debt = historical_data['2024']['Long-Term Debt']
    total_capital = market_cap + market_value_of_debt

    try:
        wacc = ((market_cap / total_capital) * cost_of_equity) + \
               ((market_value_of_debt / total_capital) * cost_of_debt * (1 - tax_rate))
    except ZeroDivisionError:
        wacc = cost_of_equity

    st.markdown("---")
    st.markdown(f"**Calculated Cost of Equity:** `{format_value(cost_of_equity, 'percentage')}`")
    st.markdown(f"**Calculated Cost of Debt:** `{format_value(cost_of_debt, 'percentage')}`")
    st.markdown(f"**Calculated WACC:** `{format_value(wacc, 'percentage')}`")

# --- Terminal Value Inputs ---
with st.sidebar.expander("♾️ Terminal Value Inputs"):
    perpetual_growth_rate = st.slider("Perpetual Growth Rate (%)", 0.0, 5.0, 2.5, 0.1, help="The long-term growth rate of cash flows beyond the projection period.") / 100

# --- Final Assumptions Dictionary ---
assumptions = {
    'revenue_growth_rate': rev_growth_override, 'cogs_percent_revenue': cogs_percent_override,
    'sga_percent_revenue': sga_percent_override, 'ar_days': ar_days, 'inventory_days': inventory_days,
    'ap_days': ap_days, 'accrued_liabilities_percent_revenue': accrued_liabilities_percent_revenue,
    'depreciation_rate': depreciation_rate, 'capex_percent_revenue': capex_percent_revenue,
    'debt_repayment_percent': debt_repayment_percent, 'tax_rate': tax_rate,
    'shares_outstanding': shares_outstanding, 'wacc': wacc, 'cost_of_equity': cost_of_equity,
    'cost_of_debt': cost_of_debt, 'perpetual_growth_rate': perpetual_growth_rate
}

# --- Model Execution ---
projection_years_list = [str(int(max(historical_data.keys())) + i) for i in range(1, 6)]
statements = build_financial_statements(assumptions, historical_data, projection_years_list)
dcf_model, metrics = build_dcf_model(statements, assumptions, projection_years_list)

# --- Main Dashboard Display ---
st.header("Valuation Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Implied Share Price", f"${metrics['Implied Share Price']:.2f}")
col2.metric("Enterprise Value", format_value(metrics['Enterprise Value'], "currency"))
col3.metric("WACC", format_value(assumptions['wacc'], "percentage"))

# --- Tabs for Detailed Analysis (Comps tab removed) ---
tab1, tab2, tab3 = st.tabs(["📊 DCF Analysis", "🧾 Financial Statements", "⚖️ WACC Breakdown"])

with tab1:
    st.subheader("Enterprise Value Bridge")
    value_bridge_data = pd.DataFrame({
        'Component': ['PV of Forecasted UFCF', 'PV of Terminal Value'],
        'Value': [metrics['Sum of PV of UFCF'], metrics['PV of Terminal Value']]
    }).set_index('Component')
    st.bar_chart(value_bridge_data)
    st.markdown(f"The analysis implies an Enterprise Value of **{format_value(metrics['Enterprise Value'], 'currency')}**.")

    st.subheader("Discounted Cash Flow (DCF) Calculation")
    st.dataframe(dcf_model.style.format("{:,.2f}"))

# NEW: Financial statements are now in separate tables
with tab2:
    st.subheader("Projected Income Statement")
    st.dataframe(statements.loc['Income Statement'].style.format("{:,.2f}"))

    st.subheader("Projected Balance Sheet")
    st.dataframe(statements.loc['Balance Sheet'].style.format("{:,.2f}"))

    st.subheader("Projected Cash Flow Statement")
    st.dataframe(statements.loc['Cash Flow Statement'].style.format("{:,.2f}"))


# NEW: WACC table is refined and formulas are moved to an expander
with tab3:
    st.subheader("WACC Calculation Breakdown")
    st.markdown("The Weighted Average Cost of Capital (WACC) is the average rate of return a company is expected to provide to all its different investors.")

    wacc_data = {
        'Component': ['Risk-Free Rate', 'Market Risk Premium', 'Company Beta', '**Cost of Equity (Ke)**',
                      'Interest Expense (2024)', 'L/T Debt (2024)', '**Cost of Debt (Kd)**',
                      'Market Cap (E)', 'Market Value of Debt (D)', 'Corporate Tax Rate', '**WACC**'],
        'Value': [format_value(risk_free_rate, 'percentage'), format_value(market_risk_premium, 'percentage'),
                  f"{company_beta:.2f}", format_value(cost_of_equity, 'percentage'),
                  format_value(historical_data['2024']['Interest Expense'], 'currency'),
                  format_value(historical_data['2024']['Long-Term Debt'], 'currency'),
                  format_value(cost_of_debt, 'percentage'),
                  format_value(market_cap, 'currency'), format_value(market_value_of_debt, 'currency'),
                  format_value(tax_rate, 'percentage'), format_value(wacc, 'percentage')]
    }
    wacc_df = pd.DataFrame(wacc_data).set_index('Component')
    st.table(wacc_df)

    with st.expander("See Formulas"):
        st.markdown("**Cost of Equity ($K_e$)**")
        st.latex(r'''
        K_e = R_f + \beta \times (R_m - R_f)
        ''')
        st.markdown(r'''
        Where:
        - $R_f$ = Risk-Free Rate
        - $\beta$ = Company Beta
        - $(R_m - R_f)$ = Market Risk Premium
        ''')

        st.markdown("**Weighted Average Cost of Capital (WACC)**")
        st.latex(r'''
        WACC = \left(\frac{E}{E+D}\right)K_e + \left(\frac{D}{E+D}\right)K_d(1-t)
        ''')
        st.markdown(r'''
        Where:
        - $E$ = Market Value of Equity (Market Cap)
        - $D$ = Market Value of Debt
        - $K_e$ = Cost of Equity
        - $K_d$ = Cost of Debt
        - $t$ = Corporate Tax Rate
        ''')


# --- Download Button ---
# NEW: Filename is now dynamic based on company name
safe_company_name = "".join([c for c in company_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
excel_file = to_excel({
    "DCF Analysis": dcf_model,
    "Financial Statements": statements,
    "WACC Breakdown": wacc_df
})
st.sidebar.download_button(
    label="📥 Download Model to Excel",
    data=excel_file,
    file_name=f"dcf_model_{safe_company_name}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

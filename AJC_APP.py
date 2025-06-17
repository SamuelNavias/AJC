import pandas as pd
import streamlit as st

# --- HTML Table Renderer ---
def render_html_table(df):
    df = df.fillna("")
    html = """
    <div style="height:600px; overflow-y:auto; overflow-x:auto;">
    <table style="border-collapse:collapse; width:100%; font-family:sans-serif;">
    <thead>
        <tr style='background-color:#f0f0f0;'>
            <th style='padding:8px;'>Name</th>
            <th style='padding:8px;'>Account</th>
            <th style='padding:8px;'>Moneys</th>
            <th style='padding:8px;'>Sheet</th>
        </tr>
    </thead>
    <tbody>
    """
    for _, row in df.iterrows():
        bg = "background-color:#fff8b3;" if row.get("Is Total", False) else ""
        html += f"<tr style='{bg}'>"
        html += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{row['Name']}</td>"
        html += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{row['Account']}</td>"
        html += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{row['Moneys']}</td>"
        html += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{row['Sheet']}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# --- Cached Excel Reader ---
@st.cache_data
def load_all_sheets_as_dataframe(file):
    all_sheets = pd.read_excel(file, sheet_name=None, header=0, engine="openpyxl")
    df_list = []
    for sheet_name, df in all_sheets.items():
        df = df.copy()
        df["Sheet"] = sheet_name
        df_list.append(df)
    return pd.concat(df_list, ignore_index=True)

# --- Cached Processing Function ---
@st.cache_data
def preprocess_and_combine(df):
    df = df.rename(columns={"Unnamed: 0": "Name"})
    df["Name"] = df["Name"].ffill()
    df["Is Total"] = df["Name"].astype(str).str.strip().str.startswith("Total ")
    df["Moneys"] = df["Amount"].combine_first(df["Credit"])
    df["Account"] = df["Account"].str.replace(r"^\d+\s*\u2211\s*", "", regex=True)

    df_total = df[df["Is Total"]]
    df_non_total = df[~df["Is Total"]]

    final = df_non_total[["Name", "Account", "Moneys", "Sheet", "Is Total"]].dropna(subset=["Moneys"])
    final_total = df_total[["Name", "Moneys", "Sheet", "Is Total"]].dropna(subset=["Moneys"])

    combined_rows = []
    sheets = sorted(final["Sheet"].unique())
    for sheet in sheets:
        donors = final[final["Sheet"] == sheet]["Name"].unique()
        for donor in donors:
            indiv = final[(final["Sheet"] == sheet) & (final["Name"] == donor)]
            total = final_total[(final_total["Sheet"] == sheet) & (final_total["Name"].str.contains(donor))]
            combined_rows.append(indiv)
            if not total.empty:
                combined_rows.append(total)
    full_table = pd.concat(combined_rows, ignore_index=True)

    return final, final_total, full_table, df.copy()

# --- Lapsed Donor Detection ---
@st.cache_data
def find_lapsed_donors(df, filter_year=None, min_last_amount=0):
    pivot = (
        df[df["Is Total"]]              # only the “Total …” rows
        .pivot_table(index="Name",
                     columns="Sheet",
                     values="Moneys",
                     aggfunc="sum",
                     fill_value=0)
        .sort_index(axis=1)
    )

    lapsed = []

    for name, row in pivot.iterrows():
        years = row.index
        gave_years = row[row > 0].index.tolist()

        # ---------- safeguard ----------
        if not gave_years:
            # Donor has no positive totals at all → skip
            continue
        # --------------------------------

        last_year     = gave_years[-1]
        last_amount   = row[last_year]
        subsequent    = years[years.get_loc(last_year) + 1 :]
        missed_years  = [y for y in subsequent if row[y] == 0]

        if missed_years and last_amount >= min_last_amount:
            if (filter_year is None) or (last_year == filter_year):
                lapsed.append({
                    "Name":            name,
                    "Last Donation Year": last_year,
                    "Lapsed In":       ", ".join(missed_years),
                    "Last Year Amount": last_amount,
                    "Total Given":     row.sum(),
                })

    return pd.DataFrame(lapsed)

# --- Streamlit Setup ---
st.set_page_config(page_title="AJC Donations", layout="wide")
st.title("📊 AJC Donation Table Viewer")

uploaded_file = st.file_uploader("Upload the AJC Excel File", type=["xlsx"])

if uploaded_file:
    with st.spinner("Processing Excel file..."):
        df = load_all_sheets_as_dataframe(uploaded_file)
        final, final_total, full_table, df_with_totals = preprocess_and_combine(df)

    # --- Filter Inputs ---
    st.subheader("🔍 Filter Table")
    search_name = st.text_input("Search Donor Name")

    sheet_values = sorted(full_table["Sheet"].dropna().unique())
    account_values = sorted(full_table["Account"].dropna().unique())

    col1, col2 = st.columns(2)
    with col1:
        sheet_filter = st.selectbox("Filter by Sheet", options=["All"] + sheet_values, index=0)
    with col2:
        account_filter = st.selectbox("Filter by Account", options=["All"] + account_values, index=0)

    # --- Apply Filters
    filtered_table = full_table.copy()
    if search_name:
        filtered_table = filtered_table[filtered_table["Name"].str.contains(search_name, case=False, na=False)]
    if sheet_filter != "All":
        filtered_table = filtered_table[filtered_table["Sheet"] == sheet_filter]
    if account_filter != "All":
        filtered_table = filtered_table[filtered_table["Account"] == account_filter]

    # --- Display Main Table
    html_table = render_html_table(filtered_table)
    st.markdown(html_table, unsafe_allow_html=True)

    # --- Pivot Table (Totals Summary) ---
    st.title("📈 Yearly Donation Totals")

    threshold = st.number_input("Minimum Donation Threshold", min_value=0, value=2500, step=100)

    pivot_df = full_table[full_table["Is Total"]].pivot_table(
        index="Name", columns="Sheet", values="Moneys", aggfunc="sum", fill_value=0
    )

    try:
        pivot_df = pivot_df[sorted(
            pivot_df.columns,
            key=lambda s: int(s.split("_")[0]),
            reverse=True
        )]
    except Exception:
        pass

    filtered_pivot = pivot_df[pivot_df.max(axis=1) >= threshold]

    def highlight_cells(val):
        if val >= threshold:
            return "background-color: #d4edda;"
        elif val > 0:
            return "background-color: #f8d7da;"
        else:
            return ""

    styled_pivot = filtered_pivot.style \
        .format("${:,.0f}") \
        .applymap(highlight_cells)

    st.dataframe(styled_pivot, use_container_width=True)

        # ───── Year‑over‑Year change table ─────
    st.header("📊 Year‑over‑Year Donation Change")

    # Ensure chronological order (oldest → newest) for diff calculation
    chrono_cols = sorted(
        pivot_df.columns,
        key=lambda s: int(s.split("_")[0])
    )
    chrono_piv = pivot_df[chrono_cols]

    # Compute absolute change vs previous year
    diff_df = chrono_piv.diff(axis=1)

    # Drop the first (oldest) column of NaNs produced by diff
    diff_df = diff_df.iloc[:, 1:]

    # Show most‑recent year on the left
    diff_df = diff_df[diff_df.columns[::-1]]

    # Allow user thresholding on absolute change (optional)
    change_threshold = st.number_input(
        "Highlight changes whose magnitude is at least:", value=0, step=1000
    )

    def delta_color(val):
        if pd.isna(val):
            return ""
        if abs(val) < change_threshold:
            return ""
        return "background-color: #d4edda;" if val > 0 else "background-color: #f8d7da;"

    st.dataframe(
        diff_df.style.format("${:,.0f}").applymap(delta_color),
        use_container_width=True
    )


    # --- Lapsed Donors Section ---
    st.title("📉 Donors Who Stopped Donating")
    st.markdown("View donors who gave in a final year and did not return.")

    all_years = sorted(df_with_totals["Sheet"].dropna().unique())
    col3, col4 = st.columns(2)
    with col3:
        selected_year = st.selectbox("Only Show Donors Whose Last Donation Was In:", ["All"] + all_years)
    with col4:
        min_last_amt = st.number_input("Minimum Last Donation Amount", min_value=0, value=2500, step=100)

    filter_year = selected_year if selected_year != "All" else None
    lapsed_df = find_lapsed_donors(df_with_totals, filter_year=filter_year, min_last_amount=min_last_amt)

    if not lapsed_df.empty:
        st.dataframe(lapsed_df, use_container_width=True)
    else:
        st.info("No lapsed donors detected based on the current filters.")

else:
    st.info("📂 Upload an Excel file to begin.")

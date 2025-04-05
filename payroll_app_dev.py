
import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

st.set_page_config(page_title="BMF Payroll Generator", layout="wide")
st.title("🟦 BMF Payroll Generator")
st.caption("Version 1.0.2 – April 2025")

st.sidebar.image("https://raw.githubusercontent.com/cmoorem5/payroll-automation/main/bmf_logo.jpg", width=200)

with st.sidebar.expander("ℹ️ How to Use This App"):
    st.markdown("""
    1. Upload the **Crew Schedule** (Excel)
    2. Upload the **Late Call Report** (Excel)
    3. Click **Generate Payroll**
    4. Review the color-coded table and download the Excel export
    """)


with st.sidebar.expander("🚧 Coming Soon"):
    st.markdown("- Export PDF summaries per employee\n- Send directly to payroll inbox\n- Role-based filtering\n- Automatic late call syncing")

st.sidebar.header("Upload Files")
schedule_file = st.sidebar.file_uploader("Upload Crew Schedule (.xlsx)", type=["xlsx"])
latecall_file = st.sidebar.file_uploader("Upload Late Call Report (.xlsx)", type=["xlsx"])

def generate_payroll(schedule_df, staff_df, late_df):
    dates = schedule_df.iloc[0, 2:12].tolist()
    date_strs = [pd.to_datetime(d).strftime('%Y-%m-%d') if pd.notna(d) else None for d in dates]
    valid_rows = schedule_df.drop(index=list(range(46, 53)) + list(range(93, 116)), errors='ignore')
    name_id_map = dict(zip(staff_df['Nurses'].astype(str).str.strip(), staff_df['ID']))

    records = []
    for _, row in valid_rows.iterrows():
        last_name = str(row[1]).strip()
        if last_name in name_id_map:
            emp_id = name_id_map[last_name]
            for i, col in enumerate(range(2, 12)):
                shift = row[col]
                if pd.isna(shift) or not isinstance(shift, str):
                    continue
                shift = shift.strip().lower()
                date = date_strs[i]
                entry = {
                    "Employee ID": emp_id,
                    "Name": last_name,
                    "Date": date,
                    "Regular Hours": 0,
                    "Sick Hours": 0,
                    "Leave Hours": 0,
                    "OT Hours": 0,
                    "AT Hours": 0,
                    "Late Call Hours": 0.0
                }
                if shift == "sick":
                    entry["Sick Hours"] = 12
                elif shift in ["lt-d", "lt-n"]:
                    entry["Leave Hours"] = 12
                elif shift == "at":
                    entry["AT Hours"] = 12
                elif shift.endswith("c"):
                    entry["OT Hours"] = 12
                else:
                    entry["Regular Hours"] = 12
                records.append(entry)

    for _, row in late_df.iterrows():
        date = pd.to_datetime(row['item_added']).strftime('%Y-%m-%d')
        emp_id = str(row['Nurse']).strip()
        hours = row['Unnamed: 11']
        if pd.notna(emp_id) and pd.notna(hours):
            records.append({
                "Employee ID": emp_id,
                "Name": None,
                "Date": date,
                "Regular Hours": 0,
                "Sick Hours": 0,
                "Leave Hours": 0,
                "OT Hours": 0,
                "AT Hours": 0,
                "Late Call Hours": float(hours)
            })

    df = pd.DataFrame(records)
    df['Name'] = df.apply(
        lambda row: row['Name'] if pd.notna(row['Name']) else (
            staff_df.loc[staff_df['ID'] == row['Employee ID'], 'Nurses'].iloc[0]
            if not staff_df.loc[staff_df['ID'] == row['Employee ID'], 'Nurses'].empty else None
        ),
        axis=1
    )
    df['Employee'] = df['Name'] + " (" + df['Employee ID'] + ")"
    ordered_dates = sorted(df['Date'].dropna().unique())
    structured_rows = []
    employees = df.dropna(subset=["Name", "Employee ID"]).drop_duplicates(subset=["Employee ID"])

    for _, emp_row in employees.iterrows():
        emp_id = emp_row["Employee ID"]
        name = emp_row["Name"]
        display_name = f"{name} ({emp_id})"
        emp_data = df[df["Employee ID"] == emp_id]

        name_row = [display_name] + [''] * len(ordered_dates)
        date_row = ["Pay Period Dates"] + [pd.to_datetime(d).strftime('%Y-%m-%d') for d in ordered_dates]

        def build_row(label, field):
            return [label] + [
                emp_data[emp_data['Date'] == d][field].sum() if d in emp_data['Date'].values else 0
                for d in ordered_dates
            ]

        structured_rows.extend([
            name_row,
            date_row,
            build_row("Regular Hours", "Regular Hours"),
            build_row("Sick Leave Hours", "Sick Hours"),
            build_row("Leave Time Hours", "Leave Hours"),
            build_row("OT Hours", "OT Hours"),
            build_row("AT Hours", "AT Hours"),
            build_row("Late Call Hours", "Late Call Hours")
        ])

    columns = [""] + [pd.to_datetime(d).strftime('%Y-%m-%d') for d in ordered_dates]
    final_df = pd.DataFrame(structured_rows, columns=columns)
    final_df["Total"] = final_df.iloc[:, 1:].apply(
        lambda row: sum([float(x) if pd.notna(x) and str(x).replace('.', '', 1).isdigit() else 0 for x in row]), axis=1
    )
    return final_df

if schedule_file and latecall_file:
    try:
        schedule_excel = pd.ExcelFile(schedule_file)
        rn_df = pd.read_excel(schedule_excel, sheet_name='RN & Medic', header=None)
        staff_df = pd.read_excel(schedule_excel, sheet_name='Staff List')
        late_df = pd.read_excel(latecall_file)

        if st.sidebar.button("Generate Payroll"):
            final_output = generate_payroll(rn_df, staff_df, late_df)
            # Append totals row at the end
            numeric_cols = final_output.select_dtypes(include="number").columns
            totals = final_output[numeric_cols].sum(numeric_only=True)
            totals_row = ["Totals"] + [""] * (len(final_output.columns) - len(totals) - 2) + totals.tolist()
            total_df = pd.DataFrame([totals_row], columns=final_output.columns)
            final_output = pd.concat([final_output, total_df], ignore_index=True)

    # Append totals row at the end
    numeric_cols = final_output.select_dtypes(include='number').columns
    totals = final_output[numeric_cols].sum(numeric_only=True)
    totals_row = ['Totals'] + ['' for _ in range(len(final_output.columns) - len(totals) - 2)] + totals.tolist()
    total_df = pd.DataFrame([totals_row], columns=final_output.columns)
    final_output = pd.concat([final_output, total_df], ignore_index=True)

            ordered_dates = list(final_output.columns[1:-1])
            midpoint = len(ordered_dates) // 2
            week1, week2 = ordered_dates[:midpoint], ordered_dates[midpoint:]

            styled = final_output.style                 .apply(lambda row: [
                    'background-color: #e6f7ff' if col and col[:10] in week1 else
                    'background-color: #fff0f5' if col and col[:10] in week2 else ''
                    for col in final_output.columns
                ], axis=1)                 .apply(lambda row: [
                    'background-color: #f2f2f2' if row.name % 8 == 0 else ''
                    for _ in row
                ], axis=1)

            
with st.sidebar.expander("🔎 Filter Options"):
    employee_filter = st.selectbox("Filter by Employee", ["Show All"] + sorted(set(final_output.iloc[::8, 0].dropna())))
    if employee_filter != "Show All":
        start_indices = final_output[final_output.iloc[:, 0] == employee_filter].index
        if not start_indices.empty:
            start_idx = start_indices[0]
            final_output = final_output.iloc[start_idx:start_idx+8]

    st.write(styled.format({col: "{:.2f}" for col in final_output.select_dtypes(include="number").columns}))

            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_output.to_excel(writer, index=False, sheet_name='Payroll')
                workbook = writer.book
                worksheet = writer.sheets['Payroll']
                week1_format = workbook.add_format({'bg_color': '#e6f7ff'})
                week2_format = workbook.add_format({'bg_color': '#fff0f5'})
                gray_format = workbook.add_format({'bg_color': '#f2f2f2'})
                for col_idx, col_name in enumerate(final_output.columns):
                    if col_name[:10] in week1:
                        worksheet.set_column(col_idx, col_idx, 15, week1_format)
                    elif col_name[:10] in week2:
                        worksheet.set_column(col_idx, col_idx, 15, week2_format)
                for i in range(0, len(final_output), 8):
                    worksheet.set_row(i + 1, None, gray_format)
                worksheet.write(len(final_output.index) + 2, 0, 'Generated by BMF Payroll Generator v1.0.2 – April 2025')

            st.download_button(
                label="📥 Download Payroll File",
                data=output.getvalue(),
                file_name=f"bmf_payroll_{datetime.date.today()}_{schedule_file.name.replace('.xlsx', '')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error processing files: {e}")
else:
    st.info("Please upload both required files to proceed.")

import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

st.set_page_config(page_title="Payroll Automation Tool", layout="wide")
st.title("📋 RN Payroll Generator")

# Sidebar for uploads
st.sidebar.header("Upload Files")
schedule_file = st.sidebar.file_uploader("Upload Crew Schedule (.xlsx)", type=["xlsx"])
latecall_file = st.sidebar.file_uploader("Upload Late Call Report (.xlsx)", type=["xlsx"])

# Helper function to generate payroll structure
def generate_payroll(schedule_df, staff_df, late_df):
    dates = schedule_df.iloc[0, 2:12].tolist()
    date_strs = [pd.to_datetime(d).strftime('%Y-%m-%d') if pd.notna(d) else None for d in dates]

    valid_rows = schedule_df.drop(index=list(range(46, 53)) + list(range(93, 116)), errors='ignore')
    name_id_map = dict(zip(staff_df['Nurses'].astype(str).str.strip(), staff_df['ID']))

    records = []
    for idx, row in valid_rows.iterrows():
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
        lambda row: row['Name'] if pd.notna(row['Name']) else staff_df.loc[
            staff_df['ID'] == row['Employee ID'], 'Nurses'
        ].values[0] if row['Employee ID'] in staff_df['ID'].values else None,
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
        emp_data = df[df["Employee ID"] == emp_id].set_index("Date")

        name_row = [display_name] + [''] * len(ordered_dates)
        date_row = ["Pay Period Dates"] + [pd.to_datetime(d).strftime('%Y-%m-%d') for d in ordered_dates]

        def build_row(label, field):
            return [label] + [emp_data.loc[d][field] if d in emp_data.index else 0 for d in ordered_dates]

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

# Main processing
if schedule_file and latecall_file:
    try:
        schedule_excel = pd.ExcelFile(schedule_file)
        rn_df = pd.read_excel(schedule_excel, sheet_name='RN & Medic', header=None)
        staff_df = pd.read_excel(schedule_excel, sheet_name='Staff List')
        late_df = pd.read_excel(latecall_file)

        st.success("Files uploaded successfully.")

        if st.sidebar.button("Generate Payroll"):
            final_output = generate_payroll(rn_df, staff_df, late_df)
            st.dataframe(final_output)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_output.to_excel(writer, index=False, sheet_name='Payroll')
            st.download_button(
                label="📥 Download Payroll File",
                data=output.getvalue(),
                file_name=f"payroll_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error processing files: {e}")
else:
    st.info("Please upload both required files to proceed.")

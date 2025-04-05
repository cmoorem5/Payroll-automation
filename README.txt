
Payroll Automation App
=======================

This Streamlit app allows you to upload a crew schedule and a late call report, then generates a payroll summary file that includes:

- Regular Hours
- Sick Leave Hours
- Leave Time Hours (LT-D, LT-N)
- Overtime Hours (with 'c' suffix)
- Administrative Time (AT)
- Late Call Hours

Instructions:
-------------

1. Install the required packages:
   pip install streamlit pandas openpyxl xlsxwriter

2. Run the app:
   streamlit run payroll_app.py

3. In the sidebar:
   - Upload your Crew Schedule Excel file (e.g., "30 Mar 2025.xlsx")
   - Upload the Late Call Report Excel file
   - Click "Generate Payroll"

4. Preview your results and click "Download Payroll File" to save the output.

Requirements:
-------------
- Python 3.x
- Streamlit
- pandas
- openpyxl
- xlsxwriter

Contact your operations scripting administrator for support.

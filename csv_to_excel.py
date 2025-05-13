import pandas as pd

csv_file = "tech_jobs_raw.csv"

df = pd.read_csv(csv_file)
print(f"Found {len(df)} records.")

excel_file = "Jobs.xlsx"
print(f"Converting to Excel format: {excel_file}")
df.to_excel(excel_file, index=False)
print(f"Successfully converted CSV to Excel!")
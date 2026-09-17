from pathlib import Path

import pandas as pd


for path in sorted(Path("data").glob("*")):
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        workbook = pd.ExcelFile(path)
        print(f"{path.name}: sheets={workbook.sheet_names}")
        for sheet in workbook.sheet_names:
            frame = pd.read_excel(path, sheet_name=sheet)
            print(f"  {sheet}: rows={len(frame)} cols={len(frame.columns)}")
            print("    columns=" + ",".join(str(column) for column in frame.columns))
    elif suffix == ".csv":
        frame = pd.read_csv(path, encoding="latin-1", sep=None, engine="python")
        print(f"{path.name}: rows={len(frame)} cols={len(frame.columns)}")
        print("  columns=" + ",".join(str(column) for column in frame.columns))

def spreadsheet_to_sql(file_path: str, table_name: str, engine):
    if file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)
    elif file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        raise ValueError("Unsupported spreadsheet format")

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    df.to_sql(
        table_name,
        con=engine,
        if_exists="append",
        index=False,
        method="multi"
    )

    return len(df)
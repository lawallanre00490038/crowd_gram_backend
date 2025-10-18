import pandas as pd
from io import BytesIO, StringIO
from fastapi import UploadFile, HTTPException


async def read_uploaded_dataframe(file: UploadFile, required_cols: set[str] | None = None) -> pd.DataFrame:
    import pandas as pd
    from io import BytesIO, StringIO
    from fastapi import UploadFile, HTTPException

    filename = file.filename.lower()
    content = await file.read()

    try:
        if filename.endswith(".csv"):
            # Try UTF-8, fallback to Windows-1252 (common in Excel exports)
            try:
                df = pd.read_csv(StringIO(content.decode("utf-8")))
            except UnicodeDecodeError:
                df = pd.read_csv(StringIO(content.decode("windows-1252")))
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(BytesIO(content), engine="openpyxl")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Upload .csv or .xlsx")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if required_cols and not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"File must contain columns: {required_cols}")
    
    # if required_cols:
    #     required_cols = set(required_cols)  # ✅ ensure it’s a set
    #     if not required_cols.issubset(df.columns):
    #         raise HTTPException(status_code=400, detail=f"File must contain columns: {required_cols}")


    return df


# async def read_uploaded_dataframe(file: UploadFile, required_cols: set[str] | None = None) -> pd.DataFrame:

#     """
#     Read uploaded file (Excel or CSV) into a pandas DataFrame.

#     Supported formats:
#       - .xlsx (Excel)
#       - .csv (Comma-separated)
#     Raises HTTPException 400 if format is unsupported or file can't be read.
#     """
#     filename = file.filename.lower()
#     content = await file.read()

#     try:
#         if filename.endswith(".csv"):
#             # decode bytes to string before reading CSV
#             df = pd.read_csv(StringIO(content.decode("utf-8")))
#         elif filename.endswith(".xlsx"):
#             df = pd.read_excel(BytesIO(content), engine="openpyxl")
#         else:
#             raise HTTPException(status_code=400, detail="Unsupported file type. Upload .csv or .xlsx")
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

#     if df.empty:
#         raise HTTPException(status_code=400, detail="Uploaded file is empty")

#     if required_cols and not required_cols.issubset(df.columns):
#       raise HTTPException(status_code=400, detail=f"File must contain columns: {required_cols}")

#     return df

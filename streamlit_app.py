import re
import json
import streamlit as st
import pandas as pd
import snowflake.connector

# ---------------- LOGIN SECTION ----------------

VALID_USERS = {
    st.secrets["auth"]["username"]: st.secrets["auth"]["password"]
}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in VALID_USERS and VALID_USERS[username] == password:
            st.session_state.authenticated = True
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid username or password")

    st.stop()

# ---------------- END LOGIN SECTION ----------------





















from snowflake.connector.pandas_tools import write_pandas


def get_connection():
    try:
        return snowflake.connector.connect(
            account=st.secrets["snowflake"]["account"],
            user=st.secrets["snowflake"]["user"],
            password=st.secrets["snowflake"]["password"],
            warehouse=st.secrets["snowflake"]["warehouse"],
            database=st.secrets["snowflake"]["database"],
            schema=st.secrets["snowflake"]["schema"],
            role=st.secrets["snowflake"]["role"],
        )
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return None


def clean_name(name):
    name = str(name)
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_").upper()

    if not name:
        name = "UPLOADED_DATA"

    if name[0].isdigit():
        name = f"T_{name}"

    return name


st.title("Upload CSV, Excel, or JSON Data to Snowflake")

st.sidebar.markdown(
    "Upload a CSV, Excel, or JSON file and save it to Snowflake."
)

uploaded_file = st.file_uploader(
    "Upload your file",
    type=["csv", "xlsx", "json"]
)

if uploaded_file is not None:
    df = None
    file_type = uploaded_file.name.split(".")[-1].lower()
    table_name = clean_name(uploaded_file.name.rsplit(".", 1)[0])

    try:
        if file_type == "csv":
            df = pd.read_csv(uploaded_file)

        elif file_type == "xlsx":
            df = pd.read_excel(uploaded_file)

        elif file_type == "json":
            data = json.load(uploaded_file)

            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.json_normalize(data)
            else:
                st.error("Unsupported JSON structure.")

    except Exception as e:
        st.error(f"Error reading file: {e}")

    if df is not None:
        df.columns = [clean_name(col) for col in df.columns]

        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str)

        st.write(f"Table name in Snowflake: `{table_name}`")
        st.dataframe(df)

        if st.button("Save to Snowflake"):
            conn = get_connection()

            if conn is not None:
                try:
                    success, nchunks, nrows, output = write_pandas(
                        conn=conn,
                        df=df,
                        table_name=table_name,
                        database=st.secrets["snowflake"]["database"],
                        schema=st.secrets["snowflake"]["schema"],
                        auto_create_table=True,
                        overwrite=True,
                        quote_identifiers=False,
                    )

                    if success:
                        st.success(
                            f"Data saved successfully to `{table_name}`. Rows loaded: {nrows}"
                        )
                    else:
                        st.error("Data upload failed.")
                        st.write(output)

                except Exception as e:
                    st.error(f"Error saving data: {e}")

                finally:
                    conn.close()

else:
    st.info("Please upload a CSV, Excel, or JSON file.")

import streamlit as st
import psycopg2
from dotenv import load_dotenv
import os
from openai import OpenAI

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# PostgreSQL connection settings
PG_CONFIG = {
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT", 5432),
    "dbname": os.getenv("PG_DATABASE"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD")
}


def get_postgres_schema():
    """
    Fetch all schemas, tables and columns from PostgreSQL
    """
    conn = psycopg2.connect(**PG_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            table_schema,
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY table_schema, table_name, ordinal_position
    """)

    rows = cursor.fetchall()

    schema_text = []

    current_table = None
    current_columns = []

    for schema_name, table_name, column_name, data_type in rows:
        table_key = f"{schema_name}.{table_name}"

        if current_table != table_key:
            if current_table:
                schema_text.append(
                    f"TABLE {current_table}({', '.join(current_columns)})"
                )

            current_table = table_key
            current_columns = []

        current_columns.append(f"{column_name}")

    if current_table:
        schema_text.append(
            f"TABLE {current_table}({', '.join(current_columns)})"
        )

    conn.close()

    return "\n".join(schema_text)


def is_safe_sql(query):
    unsafe_keywords = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "GRANT",
        "REVOKE"
    ]

    upper_query = query.upper()
    return not any(keyword in upper_query for keyword in unsafe_keywords)


def generate_sql_from_question(question):

    schema_info = get_postgres_schema()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""
You are a PostgreSQL SQL expert.

Generate ONLY valid PostgreSQL SELECT queries.

Available schema:

{schema_info}

Rules:
1. Return SQL only.
2. Use fully qualified table names schema.table.
3. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE.
4. Use PostgreSQL syntax.
"""
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    sql_query = response.choices[0].message.content.strip()

    if "```" in sql_query:
        parts = sql_query.split("```")
        if len(parts) >= 2:
            inner = parts[1].lstrip()
            if inner.lower().startswith("sql"):
                inner = inner[3:].lstrip()
            sql_query = inner.strip()

    return sql_query


def run_sql_query(query):

    conn = psycopg2.connect(**PG_CONFIG)
    cursor = conn.cursor()

    try:
        cursor.execute(query)

        results = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]

        conn.close()

        return results, columns

    except Exception as e:
        conn.close()
        return None, f"SQL error: {str(e)}"


# Streamlit UI

st.set_page_config(page_title="AI PostgreSQL Assistant")

st.title("AI PostgreSQL Assistant")

st.write(
    "Ask a question in plain English and generate PostgreSQL queries."
)

with st.form("user_question_form"):
    user_question = st.text_input(
        "What would you like to know about your data?"
    )
    submitted = st.form_submit_button("Generate SQL")

if submitted:

    sql = generate_sql_from_question(user_question)

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    if not is_safe_sql(sql):
        st.error(
            "Generated SQL appears unsafe. Please rephrase your question."
        )
        st.stop()

    results, columns_or_error = run_sql_query(sql)

    st.subheader("Results")

    if results is None:
        st.error(columns_or_error)
    else:
        import pandas as pd

        df = pd.DataFrame(results, columns=columns_or_error)

        st.dataframe(df)
import os
import time
import hashlib
import sqlparse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from groq import RateLimitError

import streamlit as st
from db import engine
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_db import lc_db

# -------------------------
# SQL Safety
# -------------------------
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT",
    "ALTER", "TRUNCATE", "CREATE"
]

def validate_sql_syntax(sql: str) -> bool:
    try:
        sqlparse.parse(sql)
        return True
    except Exception:
        return False

def validate_sql_safety(sql: str) -> bool:
    return not any(k in sql.upper() for k in FORBIDDEN_KEYWORDS)

def clean_sql_output(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

# -------------------------
# DB Execution
# -------------------------
def execute_sql_safe(sql: str):
    start= time.time()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = result.keys() if rows else None

        end= time.time()
        return {
                "success": True,
                "rows": [tuple(r) for r in rows],
                "columns": columns,
                "execution_time_ms": round((end-start)*1000,2)
            }
    except SQLAlchemyError as e:
        end = time.time()
        return {"success": False, "error": str(e),
                "execution_time_ms": round((end-start)*1000,2)}
    
def build_context(messages, max_turns=3):
        """
        Extract last N user questions for conversational context
        """
        user_msgs = [m["content"] for m in messages if m["roles"]=="user"]
        return "\n".join(user_msgs[-max_turns:])

# -------------------------
# LOVs (Cached)
# -------------------------
@st.cache_data(ttl=3600)
def load_lov_text(limit: int = 5) -> str:
    lov_queries = {
        "customers.country": """
            SELECT DISTINCT country FROM customers
            WHERE country IS NOT NULL LIMIT :limit
        """,
        "products.product_name": """
            SELECT DISTINCT product_name FROM products
            WHERE product_name IS NOT NULL LIMIT :limit
        """,
        "categories.category_name": """
            SELECT DISTINCT category_name FROM categories
            WHERE category_name IS NOT NULL LIMIT :limit
        """
    }

    lines = []
    with engine.connect() as conn:
        for col, query in lov_queries.items():
            result = conn.execute(text(query), {"limit": limit})
            values = [str(r[0]) for r in result]
            lines.append(f"{col}: {', '.join(values)}")

    return "\n".join(lines)

# -------------------------
# Prompt + LLM
# -------------------------
prompt = PromptTemplate(
    template="""
You are an expert PostgreSQL SQL generator.

Database schema:
{table_info}

Sample values:
{lovs}

Rules:
- Use PostgreSQL syntax
- Use only given tables and columns
- Check whether the asked column Exist , If Not Then say Column Does Not Exists
- Return ONLY valid SQL
- No explanations, no markdown
- Do NOT execute Delete, Alter and Update Query

Question:
{question}

SQL:
""",
    input_variables=["table_info", "lovs", "question"]
)

llm = ChatGroq(
    model=os.getenv("API_VERSION"),
    api_key=os.getenv("API_KEY"),
    temperature=0
)

chain = prompt | llm

# -------------------------
# Cached LLM Call
# -------------------------
@st.cache_data(ttl=3600)
def cached_llm_sql(question: str, table_info: str, lovs: str) -> str:
    return chain.invoke({
        "table_info": table_info,
        "lovs": lovs,
        "question": question
    }).content

# -------------------------
# Main Pipeline
# -------------------------
def process_nl_query(question: str, lov_text: str, context: str = ""):
    if not question:
        return {"success": False, "error": "Empty question"}

    # Build conversational question
    if context:
        full_question = f"""
Conversation context:
{context}

Current question:
{question}
"""
    else:
        full_question = question

    try:
        raw_sql = cached_llm_sql(
            full_question,
            lc_db.table_info,
            lov_text
        )
    except RateLimitError:
        return {"success": False, "error": "LLM rate limit exceeded"}
    except Exception as e:
        return {"success": False, "error": str(e)}

    sql_query = clean_sql_output(raw_sql)

    if not validate_sql_syntax(sql_query):
        return {"success": False, "error": "Invalid SQL syntax", "sql": sql_query}

    if not validate_sql_safety(sql_query):
        return {"success": False, "error": "Unsafe SQL detected", "sql": sql_query}
    start_time = time.perf_counter()
    result = execute_sql_safe(sql_query)
    if not result.get("success"):
        result["rows"] = []
    end_time = time.perf_counter()

    execution_time_ms = round((end_time - start_time) * 1000, 2) 
    result["execution_time_ms"] = execution_time_ms
    result["sql"] = sql_query

    if result.get("success") and result.get("rows"):
        result["rows"]= [tuple(r) for r in result["rows"]]
        
    return result









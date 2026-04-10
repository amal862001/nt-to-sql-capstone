import streamlit as st
import pandas as pd
import time
from nl_to_sql import process_nl_query, load_lov_text

MAX_CONTEXT_TURNS = 4
MAX_DISPLAY_ROWS = 200

def build_llm_context(messages, max_turns=3):
    
    """ 
    Build trimmed conversation context for LLM
    Uses last N user-assistant turns only 
    """
    context_msgs = []
    turn_count = 0

    for msg in reversed(messages):
        context_msgs.append(msg)

        if msg["role"] == "user":
            turn_count += 1
            if turn_count >= max_turns:
                break
    context_msgs.reverse()

    context = ""
    for msg in context_msgs:
        role = msg["role"].upper()
        content = msg["content"]
        context += f"{role}:{content}\n"

    return context
# -------------------------
# Page Config
# -------------------------
st.set_page_config(
    page_title="NL to SQL Chat",
    page_icon="💬",
    layout="wide"
)

st.title("Natural Language to SQL Chat")
st.caption("Ask questions about the Northwind database")

# -------------------------
# Session State Init
# -------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_input" not in st.session_state:
    st.session_state.last_input = ""

if "last_call_time" not in st.session_state:
    st.session_state.last_call_time = 0.0

if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "is_replay" not in st.session_state:
    st.session_state.is_replay = False


if "replay_query" not in st.session_state:
    st.session_state.replay_query = None

with st.sidebar:
    st.header("Query History")
    if st.session_state.query_history:
        for i,q in enumerate(st.session_state.query_history[::-1]):
            if st.button(q, key=f"replay_{i}"):
                st.session_state.replay_query =q
                st.session_state.is_replay = True
    else:
        st.write("No previous queries.")

# -------------------------
# Load LOVs (cached)
# -------------------------
lov_text = load_lov_text()

# -------------------------
# Render Chat History
# -------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------------
# User Input
# -------------------------
user_input = st.chat_input("Ask a database question...")

if st.session_state.replay_query:
    user_input = st.session_state.replay_query
    st.session_state.replay_query = None

# CRITICAL GUARD — stops refresh auto-execution
if user_input is None:
    st.stop()

user_input = user_input.strip()
if not user_input:
    st.stop()

# Prevent duplicate submit
if not st.session_state.is_replay:

    if user_input == st.session_state.last_input:
        st.stop()

# Cooldown guard
    if time.time() - st.session_state.last_call_time < 3:
      st.warning("Please wait a moment before sending another query.")
      st.stop()

# Update state
st.session_state.last_input = user_input
st.session_state.last_call_time = time.time()
st.session_state.is_replay = False

if not st.session_state.query_history or user_input != st.session_state.query_history[-1]:
    st.session_state.query_history.append(user_input)



# Store user message
st.session_state.messages.append({
    "role": "user",
    "content": user_input
})

with st.chat_message("user"):
    st.markdown(user_input)

# -------------------------
# NL → SQL → DB
# -------------------------
# Build conversation context 


with st.spinner("Generating SQL and executing query..."):
    context = build_llm_context(
        st.session_state.messages,
        max_turns =3
    )

    response = process_nl_query(
        user_input,
        lov_text,
        context
    )



sql_query = response.get("sql", "")
rows = response.get("rows", [])
columns = response.get("columns")
execution_time = response.get("execution_time_ms")

assistant_reply = f"**Generated SQL:**\n```sql\n{sql_query}\n```"

with st.chat_message("assistant"):

    tabs = st.tabs(["🧠 SQL", "📊 Result", "ℹ️ Info"])

    # ------------------ SQL TAB ------------------
    with tabs[0]:
        st.code(sql_query, language="sql")
        st.caption("Generated automatically from your question")

    # ------------------ RESULT TAB ------------------
    with tabs[1]:

        exec_time = response.get("execution_time_ms")

        if response.get("success"):
            st.success("Query executed successfully")

            if exec_time is not None:
                st.caption(f"⏱ Execution time: {exec_time} ms")

            if rows:
                if not columns:
                    columns = [f"col{i}" for i in range(len(rows[0]))]

                total_rows = len(rows)
                display_rows = rows[:MAX_DISPLAY_ROWS]

                df = pd.DataFrame(display_rows, columns=columns)
                st.dataframe(df, use_container_width=True)

                st.caption(f"Showing {len(display_rows)} of {total_rows} row(s)")

                if total_rows > MAX_DISPLAY_ROWS:
                    st.warning(
                        f"Only first {MAX_DISPLAY_ROWS} rows shown. "
                        "Refine your query for more specific results."
                    )
            else:
                st.info("Query executed successfully, but no rows were returned.")

        else:
            st.error("Query execution failed")
            st.code(response.get("error", "Unknown error"))

    # ------------------ INFO TAB ------------------
    with tabs[2]:
        if response.get("success"):
            st.success("No errors detected")
        else:
            st.error("Execution error occurred")

        if exec_time is not None:
            st.metric("Execution Time", f"{exec_time} ms")

        st.markdown("**Question:**")
        st.write(user_input)





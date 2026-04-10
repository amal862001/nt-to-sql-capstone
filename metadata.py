from sqlalchemy import inspect
from db import engine
#Inspector object to explore the database
inspector = inspect(engine)

#List tables

def list_tables():
    tables = inspector.get_table_names()
    print("Tables in Database:")
    for table in tables:
        print("-",table)
    return tables

def list_columns(table_name):
    columns = inspector.get_columns(table_name)
    for column in columns:
        print(f" {column['name']} ({column['type']}), nullable={column['nullable']}")
    return columns

def get_primary_key(table_name):
    pk= inspector.get_pk_constraint(table_name)
    print(f"Primary key for '{table_name}': {pk['constrained_columns']}")
    return pk['constrained_columns']


def get_foreign_keys(table_name):
    fks= inspector.get_foreign_keys(table_name)
    if not fks:
        print(" None")
    for fk in fks:
        print(f" Column {fk['constrained_columns']} references {fk['referred_table']}({fk['referred_columns']})")
    return fks

def print_schema_report():
    print("=== DATABASE SCHEMA REPORT ===\n")
    tables = list_tables()
    for table in tables:
        print(f"\n--- Table: {table} ---")
        print("Columns:")
        list_columns(table)
        print("Primary Key:")
        get_primary_key(table)
        print("Foreign Keys:")
        get_foreign_keys(table)
    print("\n=== END OF SCHEMA REPORT ===")

if __name__ =="__main__":
    print_schema_report()

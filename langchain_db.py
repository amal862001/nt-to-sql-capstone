from langchain_community.utilities import SQLDatabase
from db import engine

lc_db = SQLDatabase(engine)



# For testing we used print
#print("Usable tables:")
#print(lc_db.get_usable_table_names())

#print("\nDatabase Schema info: ")
#print(lc_db.table_info)
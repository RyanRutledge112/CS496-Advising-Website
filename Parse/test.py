from llama_index.readers.llama_parse import LlamaParse
import os
import json 

# Initialize LlamaParse
parser = LlamaParse(verbose=True)
# print(os.getenv("LLAMA_CLOUD_API_KEY"))

# Define file path
file_path = "Parse/personal.pdf"

json_objs = parser.get_json_result(file_path)

print(json_objs)

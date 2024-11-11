import csv
import os

folder_path = "data"

# Specify the file name
file_name = "my_text_file.txt"

# Create the full file path
file_path = os.path.join(folder_path, file_name)

# Write some text to the file
with open(file_path, "w") as file:
    file.write("This is some text in the file.")
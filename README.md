# dataspace
Simple dataspace management for CSV files.

Functionality:
Upload CSV files where field names are on the first line.
Edit file metadata including file/field descriptions, measure characteristics.
Declare that some fields are compatible with other fields (very alpha).
Download files in their original or RDF form.
Contruct a "cube" by combining files by their field.
User authorization: "admin" can upload, edit and build cubes.

Language: Python. Libraries used: flask, flask-wtf, pandas. See install.txt.

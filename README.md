# dataspace
Simple dataspace management for CSV files.

Functionality:
Upload CSV files where field names are on the first line.
Edit file metadata including file/field descriptions, measure characteristics.
Declare that some fields are compatible with other fields.
Download files in their original or RDF form.
Contruct a "cube" by combining files by their field.
User authorization: "admin" can upload, edit and build cubes.

Language: Python. Libraries used: flask, flask-wtf, chardet, pandas. See install.txt.

# Relase notes:
# 0.94 July 2020, bug fixes, tests by robobrowser added
# 0.93 July 2020, upload multiple files, min/max values
# 0.92 June 2020, basic CSV edit, bug fixes, data types, meta data changed to JSON
# 0.91 Apr 2020, line counting for viewing files
# 0.9 Jun 2019, big rewrite. RDF support, collections.
# 0.81 Jul 2018, bug fixes
# 0.8 Jun 2018, export/merge data (cube).
# 0.73 May 2018, per-file info
# 0.72 May 2018, bug fixes (of a fix), nicer upload form
# 0.7 May 2018, support delete
# 0.6 May 2018, main.html unifies the authorized/not authorized templates
# 0.5 Aug 2017, added search functionality for logged in users

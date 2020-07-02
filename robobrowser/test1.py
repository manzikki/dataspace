#This simply tests that the main page appears
#pip install robobrowser
import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

browser = RoboBrowser(history=True, parser='html.parser')
browser.open("http://localhost:5000")
title = browser.find("title")
assert "Dataspace" in str(title)
print("ok")


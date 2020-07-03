#Simple page loading tests using robobrowser.
#pip install robobrowser
import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

#1: Just check that the page appears.

browser = RoboBrowser(history=True, parser='html.parser')
browser.open("http://localhost:5000")
title = browser.find("title")
assert "Dataspace" in str(title)
print("page ok")

#rewrite the password file so that the robot can log in as admin
mypw = "5f4dcc3b5aa765d61d8327deb882cf99" #password
pwfile = open('../pw.md5','w')
pwfile.write(mypw)
pwfile.close()

#2: Log in
browser.open("http://localhost:5000/login")
forms = browser.get_forms()
#print(str(forms))
loginf = forms[0]
loginf['username'] = 'admin'
loginf['password'] = 'password'
browser.submit_form(loginf)
#login was ok?  there should be "admin" in span "user"
if "admin</span>" in str(browser.parsed):
    print("login ok")

#3: Access "editmeta" of the first data set






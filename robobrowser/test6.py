#Test cube construction using robobrowser.
#pip install robobrowser
import werkzeug
import os
import sys
import time
werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

#rewrite the password file so that the robot can log in as admin
mypw = "5f4dcc3b5aa765d61d8327deb882cf99" #password
pwfile = open('../pw.md5','w')
pwfile.write(mypw)
pwfile.close()
time.sleep(1)


#1: Just check that the page appears.

browser = RoboBrowser(history=True, parser='html.parser')
browser.open("http://localhost:5000")
title = browser.find("title")
assert "Dataspace" in str(title)
print("page ok")
ok=1

#2: Log in
browser.open("http://localhost:5000/login")
forms = browser.get_forms()
for loginf in forms:
    if 'username' in loginf.keys():
        loginf['username'] = 'admin'
        loginf['password'] = 'password'
        browser.submit_form(loginf)
        time.sleep(2)

#login was ok?  there should be "admin" in span "user"
if "admin</span>" in str(browser.parsed):
    print("login ok")
    ok+=1

#3: Go to cube builder, selecting two files
browser.open("http://localhost:5000/home/cube?fileselect=countryname-iso3-continent.csv&fileselect=gdppc.csv&twoselect=Submit")
if "Please select" in str(browser.parsed):
    print("cube file select ok")
    ok+=1

#4: Select fields
browser.open("http://localhost:5000/home/cube?countryname-iso3-continent.csv=ISO3digit&gdppc.csv=Country+Code&fieldsubmit=Submit")
if "unique values" in str(browser.parsed):
    print("cube field select ok")
    ok+=1

#5: Build cube
browser.open("http://localhost:5000/home/cube?generatecube=x")
if "Download the cube" in str(browser.parsed):
    print("cube built ok")
    ok+=1

#6: get form to view
forms = browser.get_forms()
vform = forms[0]
#print(str(vform))
browser.submit_form(vform)
if "Angola,AGO,Africa,Angola,AGO,34168.4027" in str(browser.parsed):
    print("view ok")
    ok+=1
#remove the pw file
os.remove('../pw.md5')
print(str(ok)+" of 5 ok")
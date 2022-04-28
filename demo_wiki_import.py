#adapted from https://medium.com/analytics-vidhya/web-scraping-a-wikipedia-table-into-a-dataframe-c52617e1f451
import pandas as pd # library for data analysis
import requests # library to handle requests
from bs4 import BeautifulSoup # library to parse HTML documents

# get the response in the form of html
#wikiurl="https://en.wikipedia.org/wiki/List_of_cities_in_India_by_population"
wikiurl="https://en.wikipedia.org/wiki/List_of_countries_by_life_expectancy"
table_class="wikitable sortable jquery-tablesorter"
response=requests.get(wikiurl)
print(response.status_code)
# parse data from the html into a beautifulsoup object
soup = BeautifulSoup(response.text, 'html.parser')
tables=soup.find_all('table',{'class':"wikitable"})
print(str(len(tables)))
tnum = 1
for t in tables:
    df=pd.read_html(str(t))
    df=pd.DataFrame(df[0])
    print("Table "+str(tnum))
    tnum=tnum+1
    print(df.head())


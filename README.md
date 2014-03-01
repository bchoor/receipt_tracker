#receipt scraper#

##Introduction##
A scraper to pull status of receipts. I am neither a developer nor a programmer professionally, I do have some basic programming and database skills which I put to use here. I started off playing around and put this together in a weekend and made some minor tweaks as I needed; so I'm sure some seasoned guys will find plenty wrong with this. I used MongoDB instead of the usual SQL-based dbs, simply because it was the easiest to implement given my limited knowledge of the SQL language itself, and how easy it is to use python arrays/lists/dicts when querying with pymongo. 

##Dependencies##
1. Python 2.7 (not 3.x compatible)
2. MongoDB for database
3. PyMongo (python library for MongoDB)
4. BeautifulSoup
5. Requests - this library is much cleaner for making web requests; the current implementation is using standard python library (urllib and urllib2); but if I have time I would like to move to using the Requests library instead
6. All other libraries are standard python ones.

##Additional information##
1. List of proxies is in proxies.csv in folder of scripts; if you are scrapping large number of receipts in a short window you might get your IP blocked for period of time.
2. status_scraper will create a log in folder "logs/."
3. status_exporter will create csv in folder "output/."

##Running the scripts##
Refer to how_to_run for inforamtion on how to setup and run the scripts.

#receipt scraper#

##Introduction##
A scraper to pull status of receipts. I am neither a developer nor a programmer professionally, I do have some basic programming and database skills which I put to use here. I started off playing around and put this together in a weekend and made some minor tweaks as I needed; so I'm sure some seasoned guys will find plenty wrong with this. I used MongoDB instead of the usual SQL-based dbs, simply because it was the easiest to implement given my limited knowledge of the SQL language itself, and how easy it is to use python arrays/lists/dicts when querying with pymongo. 

##Dependencies##
1. Python 2.7 (not 3.x compatible)
2. MongoDB for database
3. PyMongo (python library for MongoDB)
4. BeautifulSoup
6. All other libraries are standard python ones.


##Additional information##
1. List of proxies is in proxies.csv in folder of scripts; if you are scrapping large number of receipts in a short window you might get your IP blocked for period of time.
2. status_scraper will create a log in folder "logs/."
3. status_exporter will create csv in folder "output/."

##The Scripts##
###status_dbfill.py###
This basically looks at the ranges and identifies any gaps against the DB; whenever a gap is found, it creates a new record with the service_center/receipt_number and sets the form_type to "NEW"; this way it allows for a way for the other script (status_scraper.py) to find these new ones. The timestamp will also be updated; so when the status_scraper.py is run, it might be better to filter on only "NEW" form_type whenever your run this script. You might need to review the timestamp filter as well; since the timestamps on the new records will be very recent. I usually use a date in the future when I'm running it for the new records only; just to keep it simple.

###status_scraper.py###
This script is made up of 3 components; 1. worker threads, 2. queuemanager, 3. main thread

1. Worker threads - In simple terms, there are x number of worker threads that run; each one is assigned a case (from a queue manager), it attempts to get the case by reading (i.e. scraping) the website. It compares the record from the database with the once it scraped, and:
    1. If a change is noted, the previous status is stored in the *_old fields; and the fields are updated including a "last_changed" field which is set to the current date.
    2. If its a new case, it'll do exactly as above; though the *_old fields will be empty
    3. If no changes have occurred, only the timestamp will be updated. 
    4. If an exception occurred when reading the site (i.e. bad proxy, bad response, etc...), the case is re-queued for another worker thread to pick up. Once a worker thread completes its assigned case (or task) it will sleep for a pre-determined period of time (which you can vary). 

2. QueueManager thread - The queuemanager is responsible for making sure the queue is always full; so threads that come off of sleep have something to pickup and don't just stand idly by. On a 1s interval, it checks the size of the queue and will add cases until the queue size is a predetermined size (number of worker threads + 3; this is an arbitrary number, no basis at all for the +3, it gives a slight safety net that the worker threads finish things super fast).

3. Main thread - While worker and queuemanager threads are running; the main thread is in a loop sleeping for 1s; this was the easy way to get over the GIL issue (i.e. Ctrl+C doesn't work) in python when .join is used, so you can Ctrl+C out of it in case of an issue. Instead of using .join, the main thread uses a mechanism to exit out when those conditions are met.

4. There is an additional thread that listens for commands:
    * "1": Show Proxy Stats; 
    * "2": Show Processing Stats; 
    * "3": Reload Proxy (if you update your proxy list; 
    * "4": Exit cleanly (i.e. finish off any currently running worker threads), 
    * "5": Run in python shell (i used this for debugging if an exception occurred on a thread), 
    * "6": export db to csv at current point in time
    * "7": export the proxy good/bad stats as csv, so you can analyze which ones are not efficient. 

    As there are many printouts to the screen, it may appear as though you can't type it in, but you should just remember what you are typing and hit enter. This thread is not needed; and techincally should be part of the main, just didn't really want to mess with anything that was functional.


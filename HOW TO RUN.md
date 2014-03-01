##How to Use the Receipt Tracker

###Intro
This file provides an overview of how you would run this set of scripts. This assumes you have none of the dependencies installed.

### Installation of Dependencies
1. Install Python 2.7 (from python.org); as of this day the latest version for 2.7 is 2.7.6 and can be downloaded from here: http://python.org/download/releases/2.7.6/

2. Set you environment variable: 
  1. In Windows, you can do that from Right-Click "My Computer" > Advanced System Settings > Advanced > "Environment Variables". Under System Variables, find "PATH" and append the folder that has the python executable. 
  2. In Linux or Mac, you won't need to do anything.

3. Install pip or ez_install; pip and ez_install are package managers for Python. In other words if there are certain python libraries you need, you can install them easily through these. 
  1. Information on how to install pip: http://www.pip-installer.org/en/latest/installing.html
  2. Basically, you download the "get-pip.py" (link in the web page in the above bullet), and then run it. If your environment variable (PATH) was properly configured in #2, you should be able to just run in command prompt "python get-pip.py" in the location you have downloaded the get-pip.py file.

4. Install python libraries. In command prompt, type in 
  1. "pip install requests" to install the requests library
  2. "pip install BeautifulSoup" to install BeautifulSoup library. This is the library that does the parsing of the response back from the website and pulls the relevant information.
  2. "pip install pymongo" to install the mongo database library. a quick note is that you could use any database, but you would need to update the code wherever there are db calls. I have created a "db" class in status_scraper.py for all database calls; there aren't very many. Really only 2; 1 to pull the list to iterate through, and the 2nd to save any updates back to the DB. A dict (or dictionary) of key/value pairs (i.e. field and value) is passed back and forth; so should be easy to implement any database. One side note, a suggestion is to move out of using cursors; instead convert the cursor into a list; and I implemented a dirty "next()" function to pull the next record by using a counter.

5. Install MongoDB. I have very limited database experience, so MongoDB was simple and easy enough for me.
  1. Download MongoDB: http://www.mongodb.org/downloads
  2. Instructions for install MongoDB: http://docs.mongodb.org/manual/tutorial/install-mongodb-on-windows/

  One note is that you don't need to create a database or table (or collection); Mongo will automatically create it once a record is inserted. When you run the status_db_fill.py, it will create the records so no need to do anything once you have it ready and going.

6. Install MongoVUE, if you need a way to visually see the database (i.e. collections are equivalent to tables, and documents are equivalent to records). As your database gets bigger, you might need to add some indexes and MongoVUE helps. It also has a free version which is plenty for what I needed it for.
  1. Download MongoVUE: http://www.mongovue.com/downloads/
  2. Instructions are very straight forward; like installing any other windows programs. It's a .NET application, so it might need to download/install some updates. I am fairly certain this tool is available only for Windows.
  
7. Once you have your MongoDB running; you might need to run that in a separate command prompt. In Mac or Linux, it runs as a service (i.e. daemon). 

###Setting up the scripts
8. Edit status_dbfill.py; look at the ranges and configure as needed. for a first try, I would do just a few hundred records. Refresh your view in MongoVUE, look at the "u_cases" collection and you will find a bunch of empty records.

9. Edit status_scraper.py; find the filter parameters and change it to "NEW" for form_type, and for date put in a date in the future (just for this first time).

10. Create "proxies.csv" and enter a list of proxies. You can find free ones by googling. Each proxy server should be entered in this format xx.xx.xx.xx:port (example: 12.34.53.53:8080). Not all proxies work, so it's a good practice to keep track of how each is doing (there are some stats avail as the status_scraper.py is running - see #13)
  Create an "output" folder and a "logs" folder; this is where the logs and output files will be generated.


###Running the scripts
11. Run python status_dbfill.py
  This script will go through the range of values that you have entered in the script (see #1 under "Setting up the scripts"). It will iterate through each number within the range and if a record does not exist, it will create one. If one exists, it just skips it. When it creates a record it flags the "form_type" field as "NEW". The timestamp is also updated; the reason for even having a timestamp is because I ran into some issues at some point where if a timestamp was not established the filter for date wouldn't work correctly across the database.

12. Run python status_scraper.py. 
  For the first time as pointed out in #9, you will be seeking only "NEW" records. 

  As the script starts to run it'll print a bunch of records. You can get a variety of different stats and do a few tasks.

13. Interacting with status_scraper.py
  Amidst the bunch of text showing up on the screen there are few commands you can use to get some statistics on the scraper process. Just hit the number followed by enter.
  1. "1" - Shows Proxy stats. Displays a list of all proxies, and gives good/bad counter.
  2. "2" - Shows progress stats; i.e. how many processed, total records, estimated completion, etc.
  3. "3" - Reload proxy list. This happens if you have determined there are bad proxies, and you fix the proxies.csv file, but don't want to restart the whole process. 
  4. "4" - Exit cleanly. This commands cleans the queue, allows the cases currently being processed to finish off and then exit. It will export all I485s to output/status.csv
  5. "5" - allows executing python code. this was mostly used for debugging.
  6. "6" - Export all I485 records to the output/status.csv file
  7. "7" - Export the proxy stats (same as 1), but outputs to the output/proxies.csv; i usually plug this in excel to determine by good/bad ratio and determine which proxies to toss out. The proxy list is the only maintenance I have had to do on this script; since new ones come online and others go out.
  
14. At the end of the script; it exports all I485s to output/status.csv. You can tweak status_exporter.py to include other form_types if needed. This will impact the exports in #13 as well.


Ask me any questions through here; so I can more effectively address any issues.


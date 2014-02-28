This file provides an overview of how you would run this set of scripts. This assumes you have none of the dependencies installed.


1. Install Python 2.7 (from python.org); as of this day the latest version for 2.7 is 2.7.6 and can be downloaded from here: http://python.org/download/releases/2.7.6/

2. Set you environment variable: 
a. In Windows, you can do that from Right-Click "My Computer" > Advanced System Settings > Advanced > "Environment Variables". Under System Variables, find "PATH" and append the folder that has the python executable.
b. In Linux or Mac, you won't need to do anything.

3. Install pip or ez_install; pip and ez_install are package managers for Python. In other words if there are certain python libraries you need, you can install them easily through these. 
a. Information on how to install pip: http://www.pip-installer.org/en/latest/installing.html
b. Basically, you download the "get-pip.py" (link in the web page), and then run it. If your environment variable (PATH) was properly configured in #2, you should be able to just run in command prompt "python get-pip.py" in the location you have downloaded the get-pip.py file.

4. Install python libraries. In command prompt, type in 
a. "pip install requests" to install the requests library
b. "pip install pymongo" to install the mongo database library. a quick note is that you could use any database, but you would need to update the code wherever there are db calls. I will try to encapsulate all db calls to one class; so you can easily update for another database if you want to.

5. Install MongoDB. I have very limited database experience, so MongoDB was simple and easy enough for me.

6. Install MongoVUE, if you need a way to visually see the database (i.e. collections are equivalent to tables, and documents are equivalent to records). As your database gets bigger, you might need to add some indexes and MongoVUE helps. It also has a free version which is plenty for what I needed it for.

7. Once you have your MongoDB running; you might need to run that in a separate command prompt. In Mac or Linux, it runs as a service (i.e. daemon). 

8. Edit status_dbfill.py; look at the ranges and configure as needed. for a first try, I would do just a few hundred records. Refresh your view in MongoVUE, look at the "u_cases" collection and you will find a bunch of empty records.

9. Edit status_scraper.py; find the filter parameters and change it to "NEW" for form_type, and for date put in a date in the future (just for this first time).

10. Run python status_dbfill.py

11. Run python status_scraper.py

Ask me any questions through here; so I can more effectively address any issues.


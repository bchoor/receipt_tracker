from __future__ import with_statement
from BeautifulSoup import BeautifulSoup
from Queue import Queue
from pymongo import MongoClient
from datetime import datetime
from threading import Thread
import urllib
import urllib2
import smtplib
import time
import re
import requests
import random
import StringIO
import logging
import threading
import sys
import math
import status_exporter

url = "https://egov.uscis.gov/cris/Dashboard/CaseStatus.do"

delay = 5								# Worker thread delay
dtToday = datetime.now().replace( 		# Just get the date (remove time)
			hour=0, 
			minute=0, 
			second=0, 
			microsecond=0)  
startTime = datetime.now()				# To calculate script processing stats

# MongoDB connection details
mClient = MongoClient('mongodb://localhost:27017/')
mDb = mClient['trackitt']				# Database name
mUCases = mDb['u_cases']				# Table name (or collections)

# RegEx pattern definitions
pat_form = re.compile('.*Form(.*)[,].')
pat_lud = re.compile('[Oo]n (\w+ \d{1,2},[ ]\d{4})')
pat_casenumber = re.compile('.*(\d{10})')

# Status_summary RegEx patterns (only for I485 so far)
rePats = [
	(re.compile("fingerprint fee was accepted"), 0),
	(re.compile("mailed the new card"), 0),
	(re.compile("was not properly filed"), 0),
	(re.compile("transferred"), 0),
	(re.compile("registered this customer's new permanent"), 0),
	(re.compile("USPS reported that your new card was delivered"), 0),
	(re.compile("USPS reported that they picked up mail from USCIS"), 0),
	(re.compile("ordered production of your new card"), 0),
	(re.compile("notice requesting additional evidence or information"), 0),
	(re.compile("received this I485 APPLICATION"), 0),
	(re.compile("your (.*) was (updated|changed) relating to (your|the) I485"), 0),
	(re.compile("response to our request for evidence"), 0),
	(re.compile("mailed a notice requesting initial evidence"), 0),
	(re.compile("mailed you a denial decision notice for this case"), 0),
	(re.compile("mailed you a notice that we have approved"), 0),
	(re.compile("you were advised to resubmit payment of the filing fee"), 0),
	(re.compile("the post office returned the notice"), 0),
	(re.compile("mailed you an appointment notice for an interview"), 0),
	(re.compile("mailed the document to the address we have on file"), 0),
	(re.compile("mailed a notice acknowledging withdrawal of this application or petition I485"), 0),
	(re.compile("USPS reported that the card we mailed to you was flagged as undeliverable"), 0),
	(re.compile("post office returned the Card we mailed to you as undeliverable"), 0),
	(re.compile("ready for interview scheduling"), 0),
	(re.compile("mailed you a continuation notice regarding your I485"), 0),
	]

# Filter parameters for query
filter_forms = [						# Other forms can also be added
	#"NEW",			
    "I485"			
	]
filter_date = datetime(2014, 02, 15)	# Less than this date
filter_status = [ 						# These are ignored
	"Card/ Document Production"
	]
filter_status_summary = [				# These are ignored
	"was not properly filed",
	"transferred",
	"mailed a notice acknowledging withdrawal of this application or petition I485"
	]

# Queues
q_in = Queue(maxsize=0)
lock = threading.Lock()
numWorkers = 16

# Logging Defaults
logging.basicConfig(
	filename="logs/status_" + datetime.now().strftime("%Y-%m-%d_%H%M") + ".log", 
	level=logging.DEBUG,
	format='%(asctime)s|%(levelname)s|%(message)s')

def proxies_setup ():
	''' Loads the proxies.csv file into the proxies array. the csv file is in this
		format:
		ip_Address:port 
		XX.XX.XX.XX:XXXX
	'''
	global proxies
	lock.acquire()					# Just in case another thread is trying to access the proxies array
	try:
		proxies = []
		with open('proxies.csv','r') as f:
			for line in f.readlines():
				line = line.rstrip('\n')
				proxies.append({"link":line, "good": 0, "bad": 0})
		logging.info("Loaded proxies: %r" % proxies)
	finally:
		lock.release()	

def proxies_get ():
	''' Randomly picks a proxy from the proxy array. Consider using "random.choice"
	'''
	global proxies
	lock.acquire()
	try:
		if len(proxies) > 0:
			return proxies[random.randint(0, len(proxies)-1)]
		else:
			raise Exception(["No proxies are loaded"])
	finally:
		lock.release()

def get_page (values):
	''' get page from website. It passes the receipt_number (from values) to the
		request. It also uses a random proxy by calling proxies_get().
	'''
	data = urllib.urlencode(values)
	proxy = proxies_get()
	
	try:
		proxyHandle = urllib2.ProxyHandler({'https':'https://%s' % proxy["link"]})
		opener = urllib2.build_opener(proxyHandle)
		urllib2.install_opener(opener)
		
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req, timeout=10)

		proxy["good"] += 1
		return (response.read(), proxy)
	except urllib2.URLError, e:
		proxy["bad"] += 1
		raise Exception(["Possible timeout error with proxy %s" % proxy])
	except Exception, e:
		proxy["bad"] += 1
		raise Exception(["Issue in establishing proxy handler for: %r" % e])

def casestatus_get (serviceCenter, caseNumber):
	"""	casestatus_get
		
		Parameters:
			serviceCenter string
			caseNumber longint
		Returns:
			dict of (this is laid out exactly like document for mUCases collection):
				receipt_number: same as caseNumber
				service_center: same as serviceCenter
				status: short status
				status_description: whole status paragraph
				form_type: type of form (i.e. I-485)
				last_updated_date: RegEx from status_description
	"""
	appReceiptNum = serviceCenter + str(caseNumber)
	values = {'appReceiptNum': appReceiptNum}
	the_page = get_page(values)
	
	soup = BeautifulSoup(the_page[0])
	
	if soup.findAll('span', {'class': 'workAreaMessage'}):
		if soup.findAll('span', {'class': 'workAreaMessage'})[0].findAll('b', {'class': 'error'}):
			proxy = the_page[1]
			proxy["bad"] += 1
			proxy["good"] -= 1
			raise Exception("On proxy %s: %s" % (proxy, soup.findAll('span', {'class': 'workAreaMessage'})[0].findAll('b', {'class': 'error'})[0].text))

	if soup.findAll('div', {'class': 'caseStatusInfo'})[0].find('h4'):
		caseStatusInfo = soup.findAll('div', {'class': 'caseStatusInfo'})[0].find('h4').text.strip()
		caseStatus = soup.findAll('p', {'class': 'caseStatus'})[0].text.strip()
		caseStatus_Form = soup.findAll('div', {'class': 'widget', 'id': 'caseStatus'})[0].findAll('h3')[0].text
		form = pat_form.match(caseStatus_Form).group(1).strip()

		luds = pat_lud.search(caseStatus)
		if luds:
			lud = luds.group(1)
		else:
			lud = ""

		return ({'receipt_number': caseNumber,
				'service_center': serviceCenter,
				'status': caseStatusInfo, 
				'status_description': caseStatus, 
				'form_type': form,
				'last_updated_date': lud}, the_page[1])
	else:
		return ({'receipt_number': caseNumber,
				'service_center': serviceCenter,
				'status': "Not Available", 
				'status_description': "", 
				'form_type': "",
				'last_updated_date': ""}, the_page[1])

def fn_status_summary(statusDescription):
	status_summary = ""
	
	for rePat in rePats:
		reMatch = rePat[0].search(statusDescription)
		if reMatch:
			status_summary = reMatch.group(rePat[1])
			break
	
	return status_summary
	
def getlastcase ():
	lastcase = mUCases.find().sort([('receipt_number', -1)]).limit(1)
	if lastcase.count() > 0:
		
		return lastcase[0]['receipt_number']
	else:
		return caseNumber_start

def updateWorker(worker_num):
	global aliveThreads
	global counter
	while True:
		case = q_in.get()

		if case:
			aliveThreads += 1
			try:
				logging.info("#%s started work on receipt: %s%d" % (worker_num, case["service_center"], case["receipt_number"]))

				case_updated = casestatus_get(case["service_center"], case["receipt_number"])
				if case_updated:
					if case_updated[0]:
						if case_updated[0]["status"] != case["status"]:
							case["status_old"] = case["status"]
							case["status_summary_old"] = case["status_summary"]
							case["last_updated_date_old"] = case["last_updated_date"]
							case["status_description_old"] = case["status_description"]

							# pull in new values
							case["status"] = case_updated[0]["status"]
							case["last_updated_date"] = case_updated[0]["last_updated_date"]
							case["status_description"] = case_updated[0]["status_description"]
							case["change_date"] = dtToday
							case["status_summary"] = fn_status_summary(case["status_description"])

							if case["form_type"] == "NEW":
								case["form_type"] = case_updated[0]["form_type"]

				case["timestamp"] = datetime.now()
				lock.acquire()
				mUCases.save(case)
				counter += 1
				lock.release()
				print "%d Processed: %s%d" % (counter, case["service_center"], case["receipt_number"])

				logging.info("#%s completed work on receipt: %s%d by %s, and will sleep for %d seconds" % (worker_num, case["service_center"], case["receipt_number"], case_updated[1]["link"],delay))
				q_in.task_done()
			except Exception, e:
				# If exception, re-put into q_in queue
				errMessage = "#%s had an exception processing receipt %s%d: %r. We will retry it." % (worker_num, case["service_center"], case["receipt_number"], e)
				logging.error(errMessage)
				q_in.task_done()
				q_in.put(case)
			finally:
				aliveThreads -= 1

		time.sleep(delay)
def queueManager():
	global curCases
	global turnOff
	global aliveThreads

	while True:
		try:
			while q_in.qsize() < (numWorkers - 3) and turnOff == False:
				newCase = curCases.next()
				logging.info("queueManager adding new case to queue with receipt: %s%d" % (newCase["service_center"], newCase["receipt_number"]))
				q_in.put(newCase)
		except StopIteration, e:
			logging.info("queueManager could not find any more cases. Exiting.")
			turnOff = True
		except pymongo.errrors.CursorNotFound, e:
				logging.info("queueManager: cursor timed out; exiting. There might still be some un-finished cases, you might need to re-run the scraper.")
				# Need to figure out a way to reload the cursor, instead of forcing a turn off
				turnOff = True
		except Exception, e:
			logging.error("queueManager Exception: %r" % e)
			turnOff = True

		time.sleep(1)
def interrupter():
	global turnOff
	global proxies
	global counter
	global aliveThreads
	global totalRecords

	while True:
		try:
			inp = raw_input("> ")
			if inp == "":
				pass
			elif inp == "3":
				print "Reloading proxies...."
				proxies_setup()
				print "Proxies: %r" % proxies
			elif inp == "1":
				print "Proxy Link / Good / Bad "
				for p in proxies:
					print "%s %d/%d" % (p["link"], p["good"], p["bad"])
			elif inp == "4":
				print "Exiting cleanly. %d items will finish processing." % aliveThreads
				q_in.queue.clear()
				print "q_in size is %d" % (q_in.qsize())

				turnOff = True
			elif inp == "2":
				runningTime = (datetime.now() - startTime).total_seconds()
				print "Completed records: %d out of %d" % (counter, totalRecords)
				print "Percent completed: %0.3f%%" % (counter*1.0/totalRecords)
				print "Alive threads: %d" % aliveThreads
				print "Running time: %0.3f hr" % (runningTime/3600)
				print "Average time per record: %0.3f seconds" % (runningTime/counter)
				est = (runningTime/counter) * (totalRecords-counter)
				est_hr = math.floor(est/60/60.0)
				est_min = (est - est_hr*3600)/60.0
				print "Estimated time left: %02d:%06.3f" % (est_hr, est_min)

			elif inp == "5":
				inp2 = raw_input("Enter command >>> ")

				lock.acquire()
				try:
					exec inp2
				except Exception, e:
					print "Exception noted: %r" % e
				finally:
					lock.release()
			elif inp == "6":
				status_exporter.exportStatus()
			elif inp == "7":
				status_exporter.exportProxies(proxies)
			else:
				print "Command '%s' was not recognized" % inp
		except KeyboardInterrupt, e:
			print "Keyboard Interrupt detected"
		except Exception, e:
			print "Exception noted: %r" % e

def main():
	global curCases
	global counter
	global turnOff
	global aliveThreads
	global totalRecords

	logging.info("Started")

	proxies_setup()
	counter = 0
	turnOff = False	
	aliveThreads = 0

	curCases = mUCases.find({
		"form_type": {"$in": filter_forms}, 
		"timestamp": {"$lt": filter_date}, 
		"status": {"$nin": filter_status},
		"status_summary": {"$nin": filter_status_summary}
		}).sort([("receipt_number", 1)])

	totalRecords = curCases.count()

	print "Total Records: %d" % totalRecords

	# get first x records, and load into queue (q_in)
	if curCases.count() >= numWorkers + 1:
		for i in range(0, numWorkers + 1):
			q_in.put(curCases.next())
	elif curCases.count() > 0:
		for i in curCases:
			q_in.put(i)
	else:
		print "No records to update."
		exit(0)

	# crawler threads
	for i in range(1,numWorkers+1):
		t = Thread(target=updateWorker, args=(i,))
		t.daemon = True
		t.start()
		print "Thread '%s' started." % t.name

	# queue manager thread
	t = Thread(target=queueManager)
	t.daemon = True
	t.start()

	# interrupter thread
	t = Thread(target=interrupter)
	t.daemon = True
	t.start()

	print dtToday

	while True:
		try:
			if turnOff == True and q_in.empty() == True and aliveThreads < 1:
				break

			print q_in.qsize(), q_in.empty(), turnOff, threading.activeCount(), aliveThreads, curCases.alive
			time.sleep(5)
		except KeyboardInterrupt, e:
			print "Keyboard Interrupt detected."
			print "Processing complete for %d records\n" % counter
			logging.info("Keyboard interrupt detected. Finished processing for %d records\n" % counter)
			sys.exit(0)
		except Exception, e:
			print "Exception noted: %r" % e

	print "Processing complete for %d records\n" % counter
	logging.info("Finished processing for %d records\n" % counter)

	status_exporter.exportStatus()

if __name__ == "__main__":
	main()
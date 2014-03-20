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
import SocketServer
import json

url = "https://egov.uscis.gov/cris/Dashboard/CaseStatus.do"
numWorkers = 24							# Number of Workers
delay = 5								# Worker thread delay

dtToday = datetime.now().replace( 		# Just get the date (remove time)
			hour=0, 
			minute=0, 
			second=0, 
			microsecond=0)  
startTime = datetime.now()				# To calculate script processing stats

class db:
	# Filter parameters for query
	_filter_forms = [						# Other forms can also be added
		"NEW",			
	    "I485"			
		]
	_filter_date = dtToday # datetime(2014, 03, 9)	# Less than this date (year, month, day, hour, minute, second, millisecond)
	_filter_status = [ 						# These are ignored
		"Card/ Document Production"
		]
	_filter_status_summary = [				# These are ignored
		"was not properly filed",
		"mailed a notice acknowledging withdrawal of this application or petition I485"
		]

	_conn_u_cases = None
	u_cases = None
	u_cases_recordnumber = -1 			# u_cases_next incr 1; so we want 1st to be 0
	u_cases_totalrecords = 0

	def __init__(self):
		# DB Connection Details
		mClient = MongoClient('mongodb://localhost:27017/')
		mDb = mClient['trackitt']					# Database name
		self._conn_u_cases = mDb['u_cases']			# Table name (or collections)

	def u_cases_find(self):
		curCases = self._conn_u_cases.find({
			"form_type": {"$in": self._filter_forms}, 
			"timestamp": {"$lt": self._filter_date}, 
			"status": {"$nin": self._filter_status},
			"status_summary": {"$nin": self._filter_status_summary},
			}).sort([("receipt_number", 1)])

		# Convert cursor (curCases) results to a list of records
		# Each record is a python dict
		# By iterating through a list instead of the cursor, we don't have to worry
		# about cursor timeouts
		self.u_cases = list(curCases)
		self.u_cases_totalrecords = len(self.u_cases)

	def u_cases_next(self):
		''' Returns a Dict of field/value pairs; include the _id field for Mongo
		'''
		self.u_cases_recordnumber += 1

		if self.u_cases_recordnumber < self.u_cases_totalrecords:
			return self.u_cases[self.u_cases_recordnumber]
		else:
			raise Exception("No more records.")

	def u_cases_save(self, case):
		''' Takes a Dict of field/value pairs and saves to the database
			In Mongo, it includes the _id field which is what is used
			as key for making the save
		'''
		self._conn_u_cases.save(case)

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

# Queues
q_in = Queue(maxsize=0)
lock = threading.Lock()

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
				if line != "":
					line = line.rstrip('\n')
					proxies.append({"link":line, "good": 0, "ip_blocked": 0, "timeout": 0, "other_bad": 0})
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

def proxy_remove(ip_address_port):
	''' Removes the ipaddress:port pair
		ip_address_port example: xx.xx.xx.xx:xx
	'''
	global proxies
	try:
		# remove from proxies array
		for proxy in proxies:
			if proxy["link"] == ip_address_port:
				proxies.remove(proxy)

		# update csv file, by cycling through the updated proxies array
		with open("proxies.csv", "wb") as f:
		 	for proxy in proxies:
		 		f.write("%s\n" % proxy["link"] )

	finally:
		pass

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
		proxy["timeout"] += 1
		raise Exception(["Possible timeout error with proxy %s" % proxy])
	except Exception, e:
		proxy["other_bad"] += 1
		raise Exception(["Issue in establishing proxy handler for: %r" % e])

def casestatus_get (serviceCenter, caseNumber):
	"""	casestatus_get

		Uses BeautifulSoup to parse through the results of a request to the site.
		It has some exception handling, to identify:
			1. bad response
			2. IP blocked

		The result set is a list of:
			1. Case = Dict with keys "receipt_number", "service_center", "status", 
				"status_description", "form_type", "last_updated_date"
			2. Proxy = Dict with keys "link", "good", "bad". This is used in logging
				to keep track of any bad proxies.
	"""
	appReceiptNum = serviceCenter + str(caseNumber)
	values = {'appReceiptNum': appReceiptNum}
	the_page = get_page(values)
	
	soup = BeautifulSoup(the_page[0])
	
	if soup.findAll('span', {'class': 'workAreaMessage'}):
		if soup.findAll('span', {'class': 'workAreaMessage'})[0].findAll('b', {'class': 'error'}):
			proxy = the_page[1]
			proxy["ip_blocked"] += 1
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
	''' Status Summary extractor
		This function iterates through a list of Regular Expressions in the list
		'rePats'. rePat is pair of a re.compile object and group number; the re.compile
		object is used to search for a match using the parameter "statusDescription". If
		a match is found, it assigns the group number of the match to the return
	'''
	for rePat in rePats:
		reMatch = rePat[0].search(statusDescription)
		if reMatch:
			return reMatch.group(rePat[1])
	
	return ""
	
def updateWorker(worker_num):
	''' Worker thread
		Multiple instances of this function is spawned through main. The number is
		controlled by numWorkers defined at the top.

		This function checks the q_in queue; it if finds something it scrapes the
		website and compares the results with the database. 
			If a change is identified the current status is moved to the fields *_old; and the new status is saved. 
			If no change, then at least the timestamp is touched
	'''
	global aliveThreads
	global counter
	global lastprocessedcase
	global UCases

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
				UCases.u_cases_save(case)
				counter += 1
				lock.release()
				print "%d Processed: %s%d" % (counter, case["service_center"], case["receipt_number"])
				lastprocessedcase = "%s%d" % (case["service_center"], case["receipt_number"])

				logging.info("#%s completed work on receipt: %s%d by %s, and will sleep for %d seconds" % (worker_num, case["service_center"], case["receipt_number"], case_updated[1]["link"],delay))
				q_in.task_done()
			except Exception, e:
				# If exception, re-put into q_in queue
				errMessage = "#%s had an exception processing receipt %s%d: %r. We will retry it." % (worker_num, case["service_center"], case["receipt_number"], e)
				logging.error(errMessage)
				q_in.task_done()			# finish this task
				q_in.put(case)				# re-add it to the queue
			finally:
				aliveThreads -= 1

		time.sleep(delay)
def queueManager():
	''' queueManager
		On a 1s interval, it checks the size of q_in, and whether the "turnOff" flagged
		has been set. It will fill q_in with next cases until q_in is < numWorkers - 3	
	'''
	global UCases
	global turnOff
	global aliveThreads

	while True:
		try:
			while q_in.qsize() < (numWorkers - 3) and turnOff == False:
				newCase = UCases.u_cases_next()
				logging.info("queueManager adding new case to queue with receipt: %s%d" % (newCase["service_center"], newCase["receipt_number"]))
				q_in.put(newCase)
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
				print "Proxy Link / Good / IP Blocked / TimeOut / Bad (Other) "
				for p in proxies:
					print "%s %d/%d/%d/%d" % (p["link"], p["good"], p["ip_blocked"], p["timeout"], p["other_bad"])
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

'''
	The following classes have been implemented to allow an external process (e.g.)
	cgi-bin script running independently to get processing information statistics. It 
	also presents a set of commands that is abstracted through the cgi-bin script. 
	"GET":
		1. Stats

	"DO":
		1. export csv 
		2. reload proxy list
		3. delete a proxy server
'''
class MyTCPServer(SocketServer.ThreadingTCPServer):
	daemon_threads = True
	allow_reuse_address = True

class MyTCPServerHandler(SocketServer.BaseRequestHandler):
	''' Handler of client connections
	'''
	def handle(self):
		global turnOff
		global proxies
		global counter
		global aliveThreads
		global totalRecords

		try:
			message_in = self.request.recv(1024).strip()
			print "message_in: %s, %d" % (message_in, len(message_in)),
			if len(message_in) > 0:
				data = json.loads(message_in)
				print "%r" % data
				if data["message"] == "GET" and data["action"] == "1":
					self.request.sendall(json.dumps({
						"status": "OK",
						"request_type": "GET",
						"data": {
							"turnOff": turnOff,
							"lastprocessedcase": lastprocessedcase,
							"proxies": proxies,
							"counter": counter,
							"aliveThreads": aliveThreads,
							"totalRecords": totalRecords,
							"currentdatetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
							"starttime": startTime.strftime("%Y-%m-%dT%H:%M:%S.%f")
							}
						}))
				elif data["message"] == "DO" and data["action"] == "1":
					# export csv; copy to folder /var/www/.
					# send link of csv to requester
					status_exporter.exportStatus()
					#shutil.copy("output/status.csv", "/var/www/status.csv")
					self.request.sendall(json.dumps({
						"status": "OK",
						"request_type": "DO/1",
						"data": "status.csv"
						}))
				elif data["message"] == "DO" and data["action"] == "2":
					# reload proxy list
					proxies_setup()
					self.request.sendall(json.dumps({
						"status": "OK",
						"request_type": "DO/2",
						"data": ""
						}))
				elif data["message"] == "DO" and data["action"] == "3":
					# delete a poxy server
					proxy_remove(data["data"]["ip"])

					# 
					self.request.sendall(json.dumps({
						"status": "OK",
						"request_type": "DO/3",
						"data": data["data"]
						}))
				else:
					self.request.sendall(json.dumps({
						"status": "OK",
						"request_type": "%s/%s" % (data["message"], data["action"]),
						"data": "Not yet implemented."
						}))

		except Exception, e:
			print "Exception while receiving message: %r" % e


def server():
	global tcp_server
	tcp_server = MyTCPServer(("localhost", 8000), MyTCPServerHandler)
	tcp_server.serve_forever()

def main():
	global UCases
	global counter
	global turnOff
	global aliveThreads
	global totalRecords
	global tcp_server
	global lastprocessedcase

	lastprocessedcase = ""

	logging.info("Started")

	proxies_setup()
	counter = 0
	turnOff = False	
	aliveThreads = 0

	UCases = db()
	UCases.u_cases_find()

	totalRecords = UCases.u_cases_totalrecords
	print "Total Records: %r" % totalRecords

	# get first x records, and load into queue (q_in)
	if UCases.u_cases_totalrecords >= numWorkers + 1:
		for i in range(0, numWorkers + 1):
			q_in.put(UCases.u_cases_next())
	elif UCases.u_cases_totalrecords > 0:
		for i in UCases.u_cases:
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

	# server thread
	t = Thread(target=server)
	t.daemon = True
	t.start()

	print dtToday

	while True:
		try:
			if turnOff == True and q_in.empty() == True and aliveThreads < 1:
				tcp_server.shutdown()
				break

			print q_in.qsize(), q_in.empty(), turnOff, threading.activeCount(), aliveThreads
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
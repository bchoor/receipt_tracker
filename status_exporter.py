#status_exporter.py
import csv
from pymongo import MongoClient
from datetime import datetime

mClient = MongoClient('mongodb://localhost:27017/')
mDb = mClient['trackitt']
mUCases = mDb['u_cases']

def exportStatus():
	''' Exports records for all I485 cases. It will also discard any cases that have
		a status summary of "not properly filed", "transferred" or "withdrawal". It 
		also filters out any cases that have a status of "Not Available", which occurs
		sometimes when a case was present before, but then removed from the uscis system.

	'''
	mCases = mUCases.find({
	 	"form_type": "I485",
	 	"status_summary": {
	 		"$nin": [
	 			"was not properly filed",
	 			"mailed a notice acknowledging withdrawal of this application or petition I485"
	 		]},
	 	"status": {"$ne": "Not Available"}
	 	}).sort([("receipt_number", 1)])

	fieldnames = [	
		"receipt_number",
		"service_center",
		"status",
		"status_summary",
		"form_type",
		"last_updated_date",
		"status_old",
		"last_updated_date_old",
		"status_summary_old",
		"timestamp",
		"change_date",
		"received_date"
		]

	counter = 0
	output_filename = 'output/status.csv'

	if mCases.count() > 0:
		with open(output_filename, 'wb') as csvfile:
			writer = csv.DictWriter(
				csvfile,
				delimiter=",",
				fieldnames=fieldnames,
				extrasaction="ignore"
				)
			writer.writeheader()

			for mCase in mCases:
				writer.writerow(mCase)
				counter += 1

	zipfile(output_filename, "output/archive/status_%s.zip" % datetime.now().strftime("%m.%d.%Y"))
	print "Written %d rows to '%s'." % (counter, output_filename)

def exportProxies(proxies): # This is only called by status_scraper
	''' exportProxies will export a csv of a list of proxies that is passed to it.
		This should never be run on its own; it's run as part of the scraper. Instead,
		a proxy class needs to be implemented; and this method should be incorporated
		in there instead.
	'''
	fieldnames = [
		"link",
		"good",
		"ip_blocked",
		"timeout",
		"other_bad"
		]

	counter = 0
	output_filename = "output/status_proxies.csv"

	with open(output_filename, "wb") as csvfile:
		writer = csv.DictWriter (
			csvfile,
			delimiter=",",
			fieldnames=fieldnames,
			extrasaction="ignore"
			)
		writer.writeheader()

		for p in proxies:
			writer.writerow(p)
			counter += 1

	print "Written %d rows to '%s'." % (counter, output_filename)

def zipfile(srcfile, dstfile):
	import os
	import zipfile
	import zlib

	print "Zipping %s to %s" % (srcfile, dstfile)

	zf = zipfile.ZipFile(dstfile, "w", zipfile.ZIP_DEFLATED)
	zf.write(srcfile)

	zf.close()

def main():
	exportStatus()

if __name__ == "__main__":
	main()
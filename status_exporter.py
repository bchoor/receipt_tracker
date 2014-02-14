#uscis_status_exporter.def 
import csv
from pymongo import MongoClient

mClient = MongoClient('mongodb://localhost:27017/')
mDb = mClient['trackitt']
mUCases = mDb['u_cases']

def exportStatus():
	mCases = mUCases.find({
	 	"form_type": "I485"
	 	})

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
		"change_date"
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

	print "Written %d rows to '%s'." % (counter, output_filename)

def exportProxies(proxies): # This is only called by status_scraper
	fieldnames = [
		"link",
		"good",
		"bad"
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

def main():
	exportStatus()

if __name__ == "__main__":
	main()
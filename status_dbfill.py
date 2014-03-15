from pymongo import MongoClient
from datetime import datetime

# Enter ranges in this format; e.g.
# SC , Start     , End       , Received Date (approx)
# SRC, 1490000001, 1490030000, 10.01.2013 
# SRC, 1390400001, 1390430000, 09.01.2013

# Points of references
# SRC1390391051 (August 26)
# SRC1390395009 (September 10)
# SRC1390434002 (Last of FY13)
# SRC1490105000 Jan 3, 2014

def dbconn(connectionString, dbName, collectionName):
	mClient = MongoClient(connectionString)
	mDb = mClient[dbName]
	return mDb[collectionName]	

def case_new(serviceCenter, receiptNumber):
	case = {
			"service_center": serviceCenter,
			"receipt_number": receiptNumber,
			"status": "",
			"status_description": "",
			"status_summary": "",
			"status_old": "",
			"status_description_old": "",
			"status_summary_old": "",
			"form_type": "NEW",
			"last_updated_date": "",
			"timestamp": datetime(2014, 1, 1)
			}
	return case

def dbfill():
	mCases = dbconn("mongodb://localhost:27017/", "trackitt", "u_cases")

	caseNumberRanges = [
		('SRC', 1390390001, 1390434000, datetime(2013, 8, 22)),	
		('SRC', 1490000001, 1490105000, datetime(2013, 10, 1)),
		]

	for caseNumberRange in caseNumberRanges:
		exist = not_exist = 0
		print "Reading array....%d" % (caseNumberRange[1]) 
		caseNumbers = []
		cases = mCases.find({
			"service_center": caseNumberRange[0],
			"receipt_number": {"$gte": caseNumberRange[1], "$lte": caseNumberRange[2]}
			}, 
			{"_id":0, "receipt_number": 1}
			)

		caseNumbers = [case["receipt_number"] for case in cases]

		for caseNumber in range(caseNumberRange[1], caseNumberRange[2]+1):
			if caseNumber in caseNumbers:
				exist += 1
			else:
				mCases.insert(case_new(caseNumberRange[0], caseNumber))
				not_exist += 1

		print "done", exist, not_exist	

def dbfill_noticedates():
	mCases = dbconn("mongodb://localhost:27017/", "trackitt", "u_cases")

	caseNumberRanges = [
		('SRC', 1390390001, 1390434000, datetime(2013, 8, 21)),	
		('SRC', 1490000001, 1490105000, datetime(2013, 10, 1)),	
		]

	for caseNumberRange in caseNumberRanges:
		cases = mCases.find({
			"form_type": "I485",
			"service_center": caseNumberRange[0],
			"receipt_number": {"$gte": caseNumberRange[1], "$lte": caseNumberRange[2]}
			}).sort([("receipt_number", 1)])

		notice_date = caseNumberRange[3]

		for case in cases:
			if case["status"] == "Initial Review" and case["status_summary"] == "received this I485 APPLICATION":
				notice_date = case["last_updated_date"]

			case["received_date"] = notice_date
			mCases.save(case)
			#print case["receipt_number"], case["status"], case["status_summary"], notice_date


def main():
	dbfill_noticedates()

if __name__ == "__main__":
	main()
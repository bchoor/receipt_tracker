from pymongo import MongoClient
from datetime import datetime

# Enter ranges in this format; e.g.
# SC   Start       End        
# SRC, 1490000001, 1490030000           
# SRC, 1390400001, 1390430000,

# Points of references
# SRC1390391051 (August 26)
# SRC1390395009 (September 10)
# SRC1390434002 (Last of FY13)

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
			"timestamp": datetime.now()
			}
	return case


def main():
	mCases = dbconn("mongodb://localhost:27017/", "trackitt", "u_cases")

	caseNumberRanges =  [
							('SRC', 1490000001, 1490030000),
							('SRC', 1490030001, 1490031000),
							('SRC', 1390400001, 1390434002),
						]

	cases = mCases.find({"service_center": "SRC"}, {"_id":0, "receipt_number": 1})

	for caseNumberRange in caseNumberRanges:
		exist = not_exist = 0
		print "Reading array....%d" % (caseNumberRange[1]), 
		caseNumbers = []
		cases = mCases.find({"service_center": caseNumberRange[0],
							"receipt_number": {"$gte": caseNumberRange[1], "$lte": caseNumberRange[2]}
							}, 
							{"_id":0, "receipt_number": 1})

		for case in cases:
			caseNumbers.append(case["receipt_number"])

		for caseNumber in range(caseNumberRange[1], caseNumberRange[2]+1):
			if caseNumber in caseNumbers:
				exist += 1
			else:
				mCases.insert(case_new(caseNumberRange[0], caseNumber))
				not_exist += 1

		print "done", exist, not_exist

if __name__ == "__main__":
	main()
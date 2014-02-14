from pymongo import MongoClient

mClient = MongoClient('mongodb://localhost:27017/')
mDb = mClient['trackitt']
mUCases = mDb['u_cases']

mCases = mUCases.find({"receipt_number": {"$exists": 0}})

for mCase in mCases:
	print "%r" % mCase
	#mUCases.remove(mCase)
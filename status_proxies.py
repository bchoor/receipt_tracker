from pymongo import MongoClient
from datetime import datetime
import csv

# Proxies		
# 	ip_address	
# 	port	
# 	type	http, https, sock4, sock5
# 	good	
# 	timeout_error	
# 		timestamp
# 	block_error	
# 		timestamp
# 	other_error	
# 		timestamp


'''
Proxy refresh interval (in mins)			10		10 		10
Number of proxies							10		5		15
Average interval per proxy (in seconds)		3		3		3
	
Number of cases to be processed in interval	2000	1000	3000
Time to process 100,000 cases (hrs)			9       17      6       
'''

class proxies():
	def load(self):
		pass

	def update(self, proxy):
		pass

	def count(self):
		pass

	def importCSV(self, csv):
		



	def scrapeProxies(self, url):
		import mechanize
		from BeautifulSoup import BeautifulSoup

		br = mechanize.Browser()
		br.addheaders = [("User-agent", "Firefox")]

		response = br.open(url)
		br.select_form(nr=0)

		# Set protocol to "HTTPS" only
		cboxes = br.find_control(name="pr[]").items
		cboxes[0].selected = False
		cboxes[2].selected = False

		# Set anonymity level (remove "None")
		cboxes = br.find_control(name="a[]").items
		cboxes[0].selected = False

		# Set speed level to "Fast" only
		cboxes = br.find_control(name="sp[]").items
		cboxes[0].selected = False
		cboxes[1].selected = False

		# Set connection time to "Fast" only
		cboxes = br.find_control(name="ct[]").items
		cboxes[0].selected = False
		cboxes[1].selected = False

		# Set proxies per page to 100
		br.find_control(name="pp").items[3].selected = True

		br.submit()

		soup = BeautifulSoup(response.read())

		tbl = soup.findAll("table", {"id": "listtable"})[0]

		proxy = {
			"ip_address": "", "port": "",
			"date_added": datetime.now(),
			"ip_block_expiration": "",
			"type": ""
			}

		count = 1

		for tr in tbl.findAll("tr"):
			tds = tr.findAll("td")

			# clean_ip address obfuscation
			for sp in tds[1].findAll():
				print sp["d"], sp.text
				if sp.style == "display: none":
					print "to be decomposed"
					sp.decompose()
				else:
					pass
					#print sp

			proxy["ip_address"] = tds[1]
			proxy["port"] = tds[2].text
			proxy["type"] = tds[6].text

			#print proxy
			count += 1

			if count == 3: return 0


def main():
	p = proxies()
	p.importCSV("proxies.csv")
	p.scrapeProxies("https://hidemyass.com/proxy-list")


if __name__ == "__main__":
	main()

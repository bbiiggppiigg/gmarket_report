#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask
from flask.ext.uwsgi_websocket import GeventWebSocket
import subprocess
import os.path
from contextlib import closing
from selenium.webdriver import PhantomJS # pip install selenium
from selenium.webdriver.support.ui import WebDriverWait
import urllib2
import requests
import bs4
import MySQLdb
import time
import re
import random
from multiprocessing import Process , Queue , JoinableQueue
import logging
from subprocess import call
import sys
import urllib
import json

app = Flask(__name__)

websocket = GeventWebSocket(app)

@websocket.route('/echo')
def echo(ws):
	try:
		msg = ws.receive()
		if(len(msg)!=0):
			inputs  = msg.split(",")
			print inputs
			"""
			cmd = list()
			cmd.append('/Users/bbiiggppiigg/Sites/tt/search2.py')
			ws.send(msg)
			filename = '%s.out' % msg
			if os.path.isfile(filename):
				with open((msg+'.out')) as f:
					ws.send(f.read())
				return

			with open(filename,"w") as f:
				proc = subprocess.Popen(cmd+inputs, stdout=(f))
				proc.wait()

			with open((msg+'.out')) as f:
				ws.send(f.read())	
			"""
			gen_results(ws,inputs)
	except Exception ,e :
		print e
		ws.send(str(e))
		
if __name__ == '__main__':
    app.run(master=True,host='localhost',processes=8,threaded=True)


def gen_url(keyword):
	stri = "http://gsearch.gmarket.co.kr/Listview/Search?"+keyword+"&GdlcCd=100000003&pageSize=500"
	return stri

def gen_dict(soup,remainder_count = 0):
	result = dict()
	item_list = soup.find('tbody')	
	for item in item_list.find_all('tr'):
		item_name_tag =  item.find('li','item_name')
		price_tag = item.find('li','discount_price').text
		product_name = item_name_tag.text.replace('\t','').replace('\n','')
		item_url =  re.search('http://.*(?=\')',item_name_tag.find('a')['href']).group(0)
		price = int(price_tag.replace(u"￦","").replace(",",""))
		seller = item.find('ul','seller').a.text
		result[item_url] = (product_name,price,seller)
	
	return result

def fetch_pages(q,keyword):
	f = { 'keyword' : keyword}
	s = urllib.urlencode(f)
	url_base = gen_url(s)
	print url_base
	result = {}
	with closing (PhantomJS()) as browser:
		try:
			browser.get(url_base+"&page="+str(1))
			WebDriverWait(browser, timeout=30).until(lambda x: x.find_element_by_id('sItemCount'))
			page_source = browser.page_source
			soup =  bs4.BeautifulSoup(page_source,"lxml")
			
			item_count = soup.find(id="sItemCount");
			print item_count.text
			try:
				item_count =  int(item_count.text.replace(",",""))	
			except Exception , e:
				print "0 results"
				q.put(result)
				return
				
			fetch_item_count = item_count 
			fetch_page_count = fetch_item_count / 500
			remainder_count = fetch_item_count % 500
			if(remainder_count!=0):
				fetch_page_count = fetch_page_count+1
			print(fetch_item_count,fetch_page_count,remainder_count)
		except Exception , e:
			logging.warning("Fetch Source Exception : " + str(e) ) 
			raise
			
		result.update( gen_dict(soup))
		time.sleep(1.5)
		for x in range(fetch_page_count-1):
			browser.get(url_base+"&page="+str(x+2))
			WebDriverWait(browser, timeout=20).until(lambda x: x.find_element_by_id('sItemCount'))
			page_source = browser.page_source
			soup =  bs4.BeautifulSoup(page_source,"lxml")
			if(x==fetch_page_count-1 and remainder_count!=0 ):
				result.update(gen_dict(soup,remainder_count))
			else:
				result.update(gen_dict(soup))
			time.sleep(1.5)
	q.put(result);

def gen_results(ws,argvs):
	try:
		result = {}
		sellers ={}
		seller_list = list()
		q = JoinableQueue()
		for x in range(len(argvs)):
			p = Process(target=fetch_pages,args=(q,argvs[x]))
			p.start()
		
		for x in range(len(argvs)):
			result.update(q.get())
		print "HI"
		if(len(result)==0):
			ws.send("0 Results");
			return
		total_count = len(result)
		total_price = 0
		for url in result:
			(product_name,price,seller) = result[url]
			total_price = price+total_price
			if seller not in sellers:
				sellers[seller] = list()
			sellers[seller].append((product_name,price,url))
			
		for key, value in sellers.iteritems():
		    temp = [key,value]
		    seller_list.append(temp)	

		seller_list = sorted(seller_list,key=lambda x: -len(x[1]))
		avg_price = total_price / total_count		
		print "<table>"
		print "<tr><th>Number of Matching Product</th><td>"+str(total_count)+"</td></tr>"
		print "<tr><th>Average Price</th><td>"+str(avg_price)+"</td> </tr>"
		print "<tr><th>Number of Matching Seller</th><td>"+str(len(sellers))+"</td></tr>"
		print "</table>"
		#print sellers
		print "<table>"
		print "<tr><th>Seller ID</th><th>Number of Matching Products</th></tr>"
		for x in seller_list:
			print "<tr><td>"+x[0].encode('utf-8')+"</td><td>"+str(len(x[1]))+"</td></tr>"
		print "</table>"
		return_data = {};
		return_data['num_products']=total_count
		return_data['avg_price']=avg_price
		return_data['num_sellers']=len(sellers)
		return_data['seller_list']=seller_list;
		json_data = json.dumps(return_data)
		print json_data
		"""
		ws.send("<table>")
		ws.send("<tr><th>Number of Matching Product</th><td>"+str(total_count)+"</td></tr>")
		ws.send( "<tr><th>Average Price</th><td>"+str(avg_price)+"</td> </tr>")
		ws.send("<tr><th>Number of Matching Seller</th><td>"+str(len(sellers))+"</td></tr>")
		ws.send("</table>")

		ws.send("<table>")
		ws.send("<tr><th>Seller ID</th><th>Number of Matching Products</th></tr>")
		for x in seller_list:
			ws.send("<tr><td>"+x[0].encode('utf-8')+"</td><td>"+str(len(x[1]))+"</td></tr>")
		ws.send("</table>")

		"""
		ws.send(json_data)

	except Exception, e:
		print e
    

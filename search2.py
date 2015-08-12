#!/usr/bin/python
# -*- coding: utf-8 -*-

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
def gen_url(keyword):
	#stri  = "http://glistings.gmarket.co.kr/Listview/Searchkeyword="+str(keyword)+"&pageSize=500&GdlcCd=100000003"
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
		seller = item.find('ul','seller').text
		result[item_url] = (product_name,price,seller)
	
	return result

def fetch_feature(q,keyword):
	f = { 'keyword' : keyword}
	s = urllib.urlencode(f)
	
	#url_base = gen_url(keyword);
	url_base = gen_url(s)
	print url_base
	#url_base = gen_url(keyword.encode('utf-8'))
	result = {}
	with closing (PhantomJS()) as browser:
		try:
			browser.get(url_base+"&page="+str(1))
			WebDriverWait(browser, timeout=30).until(lambda x: x.find_element_by_id('sItemCount'))
			page_source = browser.page_source
			soup =  bs4.BeautifulSoup(page_source,"lxml")
			#print soup
			
			item_count = soup.find(id="sItemCount");
			print item_count.text
			item_count =  int(item_count.text.replace(",",""))	
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

def main():
	try:
		result = {}
		sellers ={}
		seller_list = list()
		q = JoinableQueue()
		for x in range(len(sys.argv)-1):
			p = Process(target=fetch_feature,args=(q,sys.argv[x+1]))
			p.start()
		
		for x in range(len(sys.argv)-1):
			result.update(q.get())

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
		
		#print total_price, total_count ,avg_price
		print "<tr>Average Price is : "+str(avg_price)+" of total "+str(total_count)+" matching products</tr>";
		print "<tr>Matched seller count is : "+str(len(sellers))+"</tr>"
		#print sellers
		for x in seller_list:
			print "<tr><td>"+x[0].encode('utf-8')+"</td><td>"+str(len(x[1]))+"</td></tr>"
	except Exception, e:
		print e

if __name__=='__main__':
    if(len(sys.argv) < 2):
    	print "Usage : <keyword> "
    	sys.exit(-1)
    main() 		
    call(["pkill", "phantomjs"])
    print "par_crawler main thread after execution"
    

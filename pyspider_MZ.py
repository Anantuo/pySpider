from pyspider.libs.base_handler import *
from my import My
from bs4 import BeautifulSoup
import hashlib
import re
import os
import redis
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.parse import urlunparse
'''梅州'''

class Handler(My):
    name = "MZ"
    mkdir = '/home/sheldon/web/'

    @every(minutes=24 * 60)
    def on_start(self):
        self.crawl('http://www.meizhou.gov.cn/open/index.php?NodeID=872&u=19&page=1', callback=self.index_page)

    def index_page(self, response):
        soup = BeautifulSoup(response.text)
        page_count = int(soup('div', {'class':'pages'})[0].find_all('a')[-1]['href'].split('&')[-1].split('=')[-1])

        url = response.url[:-1]
        for i in range(2, page_count + 1):
            link = url + str(i)
            self.crawl(link, callback=self.next_list)

        lists = soup('ul', {'class':'dotlist'})[0].find_all('li')
        for i in lists:
            link = i.find('a')['href']
            self.crawl(link, callback=self.content_page)

    @config(priority=2)
    def next_list(self, response):
        soup = BeautifulSoup(response.text)
        lists = soup('ul', {'class':'dotlist'})[0].find_all('li')
        for i in lists:
            link = i.find('a')['href']
            self.crawl(link, callback=self.content_page)
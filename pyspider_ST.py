from pyspider.libs.base_handler import *
from bs4 import BeautifulSoup
import hashlib
import re
import os
import redis
from urllib.parse import urljoin 
from urllib.parse import urlparse
from urllib.parse import urlunparse
'''汕头'''

class Handler(BaseHandler):
    name = "ST"
    mkdir = '/home/sheldon/web/'
    r = redis.Redis()
    key = 'download'
    headers= {
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding":"gzip, deflate, sdch",
        "Accept-Language":"zh-CN,zh;q=0.8",
        "Cache-Control":"max-age=0",
        "Connection":"keep-alive",
        "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36"
    }
    crawl_config = {
        "headers" : headers,
        "timeout" : 100
    }

    @every(minutes=24 * 60)
    def on_start(self):
        self.crawl('http://www.stghj.gov.cn/Category_218/Index.aspx', callback=self.index_page)
        self.crawl('http://www.stghj.gov.cn/Category_217/Index.aspx', callback=self.index_page)
        self.crawl('http://www.stghj.gov.cn/Category_221/Index.aspx', callback=self.index_page)
        self.crawl('http://www.stghj.gov.cn/Category_295/Index.aspx', callback=self.index_page)
        self.crawl('http://www.stghj.gov.cn/Category_292/Index.aspx', callback=self.index_page)
        self.crawl('http://www.stghj.gov.cn/Category_276/Index.aspx', callback=self.index_page)
        self.crawl('http://www.stghj.gov.cn/Category_279/Index.aspx', callback=self.index_page)

    # @config(age=10 * 24 * 60 * 60)
    @config(age = 1)
    def index_page(self, response):
        soup = BeautifulSoup(response.text)

        t = soup('div', {'class':'pagecss'})[0].find_all('a')[-1]['href']
        page_count = int(t.split('.')[0].split('_')[1])

        url = response.url[:-5]
        for i in range(2, page_count + 1):
            link = url + '_' + str(i) + '.aspx'
            self.crawl(link, callback=self.next_list)

        t = soup('ul', {'class':'News_list'})[0].find_all('li')
        domain = 'http://www.stghj.gov.cn'
        for i in t:
            link = domain + i.find_all('a')[1]['href']
            print(link)
            self.crawl(link, callback=self.content_page)

    @config(priority=2)
    def next_list(self, response):
        soup = BeautifulSoup(response.text)
        t = soup('ul', {'class':'News_list'})[0].find_all('li')
        domain = 'http://www.stghj.gov.cn'
        for i in t:
            link = domain + i.find_all('a')[1]['href']
            print(link)
            self.crawl(link, callback=self.content_page)

    def real_path(self, path):
        arr = urlparse(path)
        real_path = os.path.normpath(arr[2])
        return urlunparse((arr.scheme, arr.netloc, real_path, arr.params, arr.query, arr.fragment))

    @config(priority=2)
    def content_page(self, response):
        attachment = response.doc('a[href*=".doc"]') + response.doc('a[href*=".pdf"]') + response.doc('a[href*=".jpg"]') + response.doc('a[href*=".png"]') + response.doc('a[href*=".gif"]')
        images = response.doc('img')
        
        url = response.url
        m = hashlib.md5()
        m.update(url.encode())
        web_name = '/' + m.hexdigest() + '/'
        path = self.mkdir + self.name + web_name
        if not os.path.exists(path):
            os.makedirs(path)           

        image_list = []
        if images is not None:
            for each in images.items():
                image_url = self.real_path(urljoin(url, each.attr.src))
                if image_url not in image_list:
                    image_list.append(image_url)
            for i in image_list:
                d = {}
                d['url'] = i
                d['type'] = 'image'
                d['path'] = path
                self.r.rpush(self.key, str(d))

        attachment_list = []
        if attachment is not None:
            for each in attachment.items():
                if each.attr.href not in attachment_list and each.attr.href not in image_list:
                    attachment_list.append(each.attr.href)
            for i in attachment_list:
                d = {}
                d['url'] = i
                d['type'] = 'attachment'
                d['path'] = path
                self.r.rpush(self.key, str(d))

        return {
            "url": response.url,
            "html": response.text,
        }

    def on_result(self, result):
        if result is not None: 
            m = hashlib.md5()
            m.update(result['url'].encode())
            web_name = '/' + m.hexdigest() + '/'
            path = self.mkdir + self.name + web_name
            if not os.path.exists(path):
                os.makedirs(path)           

            page_path = path + 'page.txt'
            f = open(page_path, 'wb')
            f.write(result['html'].encode('utf-8'))
            f.close()
            content_path = path + 'content.txt'
            f = open(content_path, 'wb')
            soup = BeautifulSoup(result['html'])
            for i in soup('style') + soup('script'):
                i.extract()
            content = soup.decode('utf-8')
            content = re.sub(r'<[/!]?\w+[^>]*>', '', content)
            content = re.sub(r'\s+', '', content)
            f.write(content.encode('utf-8'))
            f.close()
            url_path = path + 'url.txt'
            f = open(url_path, 'wb')
            f.write(result['url'].encode('utf-8'))
            f.close()
        super(Handler, self).on_result(result)
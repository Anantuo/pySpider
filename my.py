from pyspider.libs.base_handler import *
from bs4 import BeautifulSoup
import mysql.connector
import hashlib
import time
import re
import os
import redis
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.parse import urlunparse
from urllib.parse import quote
'''放到python环境目录的site-packages下'''
class My(BaseHandler):

    r = redis.Redis()
    download_key = 'download'
    analysis_key = 'analysis'

    conn = mysql.connector.connect(user='root', password='254478_a', database='mydb')
    cursor = conn.cursor(dictionary=True)

    table_name = ['选址意见书', '建设用地规划许可证', '建设工程规划许可证', '乡村建设规划许可证',
                '规划验收合格证', '工程规划验收合格通知书', '批前公示', '批后公布']

    city_name = {'CZ':'潮州', 'DG':'东莞', 'FS':'佛山', 'GZ':'广州', 'GZ_after':'广州',
                 'HY':'河源', 'HZ':'惠州', 'JM':'江门', 'JM_X':'江门', 'JY':'揭阳', 'MM':'茂名',
                 'MZ':'梅州', 'QY':'清远', 'SG':'韶关', 'ST':'汕头', 'SW':'汕尾', 'SZ':'深圳', 
                 'YF':'云浮', 'YJ':'阳江', 'ZH':'珠海', 'ZJ':'湛江', 'ZQ':'肇庆', 'ZS':'中山'}

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
    def on_start(self):
        print('on_start')
        print(type(self))
        pass

    # def index_page(self, response):
    #     pass

    # def next_list(self, response):
    #     pass
    def get_date(self):
        return time.strftime("%Y-%m-%d", time.localtime())

    def real_path(self, path):
        arr = urlparse(path)
        real_path = os.path.normpath(arr[2])
        return urlunparse((arr.scheme, arr.netloc, real_path, arr.params, arr.query, arr.fragment))

    def js_css_download(self, response):
        # 存储位置
        path = response.save['path']
        file_name = response.save['name']
        # 创建目录
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path + file_name, 'w') as f:
            f.write(response.text)

    @config(priority=2)
    def content_page(self, response):
        url = response.url
        m = hashlib.md5()
        m.update(url.encode())
        web_name = '/' + m.hexdigest() + '/'
        path = self.mkdir + self.name + web_name
        if not os.path.exists(path):
            os.makedirs(path)           

        soup = BeautifulSoup(response.text)

        script_tag = soup.find_all('script', src=True)
        for each in script_tag:
            js_m = hashlib.md5()
            js_m.update(each['src'].encode())
            js_name = js_m.hexdigest()
            # 获取访问地址
            request_url = self.real_path(urljoin(url, each['src']))
            # 改动网页 css 地址为相对地址
            each['src'] = js_name + '.js'
            # 爬取css文件
            self.crawl(request_url, fetch_type='js', callback = self.js_css_download, save = {'path':path, 'name':each['src']})

        css_tag = soup.find_all('link', type='text/css')
        for each in css_tag:
            css_m = hashlib.md5()
            css_m.update(each['href'].encode())
            css_name = css_m.hexdigest()
            # 获取访问地址
            request_url = self.real_path(urljoin(url, each['href']))
            # 改动网页 css 地址为相对地址
            each['href'] = css_name + '.css'
            # 爬取css文件
            self.crawl(request_url, callback = self.js_css_download, save = {'path':path, 'name':each['href']})

        images = soup('img')
        image_list = []
        if images is not None:
            for each in images:
                image_url = self.real_path(urljoin(url, each['src']))
                k = image_url.split('/')
                link = k[0]
                for i in k[1:]:
                    link += '/'+ quote(i)
                image_url = link
                if image_url not in image_list:
                    # t = re.search('.asp', image_url)
                    # if t is None:
                    image_list.append(image_url)
                    d = {}
                    d['type'] = 'image'
                    d['path'] = path
                    d['url'] = image_url
                    m = hashlib.md5()
                    m.update(image_url.encode())
                    if re.search('.jpg', image_url) is not None:
                        each['src'] = m.hexdigest() + '.jpg'
                    elif re.search('.png', image_url) is not None:
                        each['src'] = m.hexdigest() + '.png'
                    elif re.search('.gif', image_url) is not None:
                        each['src'] = m.hexdigest() + '.gif'
                    d['name'] = each['src']
                    self.r.rpush(self.download_key, str(d))

        attachments = soup('a', {'href': re.compile(r'^http')})
        attachment_list = []
        if attachments is not None:
            for each in attachments:
                href = each['href']
                type_name = None
                if re.search('.jpg', href) is not None:
                    type_name = 'jpg'
                elif re.search('.png', href) is not None:
                    type_name = '.png'
                elif re.search('.gif', href) is not None:
                    type_name = '.gif'
                elif re.search('.doc', href) is not None:
                    type_name = '.doc'
                elif re.search('.pdf', href) is not None:
                    type_name = '.pdf'
                elif re.search('.zip', href) is not None:
                    type_name = '.zip'
                elif re.search('.rar', href) is not None:
                    type_name = '.rar'
                if type_name is not None:
                    attachment_url = self.real_path(urljoin(url, href))
                    k = attachment_url.split('/')
                    link = k[0]
                    for i in k[1:]:
                        link += '/'+ quote(i)
                    attachment_url = link
                    if attachment_url not in attachment_list and attachment_url not in image_list:
                       attachment_list.append(href)
                       d = {}
                       d['type'] = 'attachment'
                       d['path'] = path
                       d['url'] = attachment_url
                       m = hashlib.md5()
                       m.update(attachment_url.encode())
                       each['href'] = m.hexdigest() + '.' + type_name
                       d['name'] = each['href']
                       self.r.rpush(self.download_key, str(d))

        # 针对 background 属性
        for key in soup.find_all(background=True):
            image_url = self.real_path(urljoin(url, key['background']))
            k = image_url.split('/')
            link = k[0]
            for i in k[1:]:
                link += '/'+ quote(i)
            image_url = link
            if image_url not in image_list:
                image_list.append(image_url)
                d = {}
                d['type'] = 'image'
                d['path'] = path
                d['url'] = image_url
                m = hashlib.md5()
                m.update(image_url.encode())
                if re.search('.jpg', image_url) is not None:
                    each['src'] = m.hexdigest() + '.jpg'
                elif re.search('.png', image_url) is not None:
                    each['src'] = m.hexdigest() + '.png'
                elif re.search('.gif', image_url) is not None:
                    each['src'] = m.hexdigest() + '.gif'
                d['name'] = each['src']
                self.r.rpush(self.download_key, str(d))

        return {
            "url": url,
            "html": str(soup),
            "type": response.save['type']
        }


    def on_result(self, result):
        if result is not None: 
            m = hashlib.md5()
            m.update(result['url'].encode())
            web_name = '/' + m.hexdigest() + '/'
            path = self.mkdir + self.name + web_name
            if not os.path.exists(path):
                os.makedirs(path)           

            page_path = path + 'page.html'
            f = open(page_path, 'wb')
            f.write(result['html'].encode('utf-8'))
            f.close()

            content_path = path + 'content.txt'
            soup = BeautifulSoup(result['html'], 'html.parser')
            for i in soup('style') + soup('script'):
                i.extract()
            content = soup.decode('utf-8')
            content = re.sub(r'<[/!]?\w+[^>]*>', '\n', content)
            content = re.sub(r'<!--[\w\W\r\n]*?-->', '\n', content)
            content = re.sub(r'\s+', '\n', content)

            # url_path = path + 'url.txt'
            # f = open(url_path, 'wb')
            # f.write(result['url'].encode('utf-8'))
            # f.close()

            print(self.get_date())
            values = [result['url'].encode('utf-8'), path, 
                    self.get_date(), self.city_name[self.name].encode('utf-8'), 
                    result['type'].encode('utf-8'), content.encode('utf-8')]
            self.cursor.execute('''insert into tbl_OrglPblc values ('', %s, %s, 0, 2, %s, %s, %s, %s)''', values)

            # print(self.cursor.lastrowid)
            d = {}
            d['rowid'] = self.cursor.lastrowid
            d['path'] = path
            d['city'] = self.name
            d['type'] = result['type'].encode('utf-8')
            self.conn.commit()
            self.r.rpush(self.analysis_key, str(d))

        super(My, self).on_result(result)
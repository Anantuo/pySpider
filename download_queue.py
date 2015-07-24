import os
import hashlib
import redis
import http
import urllib.request
from urllib.parse import unquote
from PIL import Image
from io import BytesIO
def download_attachment(url, path):
	try:
		m = hashlib.md5()
		m.update(url.encode())
		try:
			name = os.path.basename(url)
			name = unquote(name)
			attachment_path = path + name
			try:
				f = urllib.request.urlopen(url)
			except http.client.HTTPException:
				opener = urllib.request.build_opener()
				headers= {
				"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
				"Accept-Encoding":"gzip, deflate, sdch",
				"Accept-Language":"zh-CN,zh;q=0.8",
				"Cache-Control":"max-age=0",
				"Connection":"keep-alive",
				"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36"
				}
				opener.addheaders = headers.items()
				f = opener.open(url)
			with open(attachment_path, 'wb') as code:
				code.write(f.read())
		except OSError:
			attachment_path = path + m.hexdigest() + '.' + url.split('.')[-1]
			f = urllib.request.urlopen(url)
			with open(attachment_path, 'wb') as code:
				code.write(f.read())
	except urllib.request.HTTPError:
		print('404')

def download_image(url, path):
	height = 400
	width = 400
	try:
		try:
			f = urllib.request.urlopen(url)
		except http.client.HTTPException:
			opener = urllib.request.build_opener()
			headers= {
			"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
			"Accept-Encoding":"gzip, deflate, sdch",
			"Accept-Language":"zh-CN,zh;q=0.8",
			"Cache-Control":"max-age=0",
			"Connection":"keep-alive",
			"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36"
			}
			opener.addheaders = headers.items()
			f = opener.open(url)
		if height * width == 0:
			image_path = path + os.path.basename(url)
			with open(image_path, 'wb') as code:
				code.write(f.read())
		else:
			i = Image.open(BytesIO(f.read()))
			temp_width, temp_height = i.size
			if temp_width >= width and temp_height >= height:
				image_path = path + os.path.basename(url)
				try:
					i.save(image_path)
				except KeyError:
					m = hashlib.md5()
					m.update(os.path.basename(url).encode())
					i.save(path + m.hexdigest() + '.' + i.format)
	except urllib.request.HTTPError:
		print('404')

if __name__ == '__main__':
	r = redis.Redis()
	key = 'download'
	while True:
		s = r.blpop(key, 0)[1]
		print(s)
		d = eval(s)
		path = d['path']
		url = d['url']
		link_type = d['type']
		if link_type == 'image':
			download_image(url, path)
		else:
			download_attachment(url, path)
		print('done')

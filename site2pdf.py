import asyncio
import hashlib
import os
import subprocess
import sys
from urllib.parse import urlparse, urljoin, urldefrag
import shutil
import pprint

import requests
from PyPDF2 import PdfFileReader, PdfFileMerger
from bs4 import BeautifulSoup


class Site2PDF():
    def __init__(self, base_url, file_name):
        self.base_url = base_url
        self.file_name = file_name
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/70.0.3538.110 Safari/537.36 '
        }
        self.content_list = []

    def run(self):
        content_urls = self.collect_urls(self.base_url)
        self.content_list = ["" for _ in range(len(content_urls))]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.crawl_content(content_urls))
        loop.close()

        pprint.pprint(self.content_list)

        # PDF merge
        merger = PdfFileMerger()
        for f in self.content_list:
            filename = os.path.basename(f)
            print('Appending ' + filename + '...')
            try:
                fs = open(filename, 'rb')
                merger.append(PdfFileReader(fs), import_bookmarks=False)
                fs.close()
                tmpdir = self.md5(self.base_url)
                if os.path.isdir(tmpdir):
                    shutil.rmtree(tmpdir)
                os.mkdir(tmpdir)
                dst = './%s/%s' % (tmpdir, f)
                shutil.move(filename, dst)
            except Exception as e:
                print(e)

        merger.write(self.file_name)

    def collect_urls(self, start_url):
        response = requests.get(start_url, headers=self.headers)
        self.base_url = response.url
        base_o = urlparse(self.base_url)
        text = response.text
        soup = BeautifulSoup(text, 'html.parser')
        links = soup.find_all('a')
        urls = set()
        for link in links:
            absolute_link = urljoin(self.base_url, link.attrs['href'])
            o = urlparse(absolute_link)
            if base_o[1] == o[1]:
                fixed, throwaway = urldefrag(absolute_link)
                urls.add(fixed)
        return urls

    async def crawl_content(self, content_urls):
        tasks = []
        for index, url in enumerate(content_urls):
            tasks.append(self.getpdf(index, url))
        await asyncio.gather(*tasks)
        print('crawl : all done!')

    async def getpdf(self, index, url):
        print('crawling : ', url)
        response = requests.get(url, headers=self.headers)
        text = response.text
        soup = BeautifulSoup(text, 'html.parser')
        title = soup.find('title')
        if len(title.string) > 0:
            file = '%s.pdf' % title.string
        else:
            file = '%s.pdf' % self.md5(url)

        subprocess.call(['/usr/local/bin/wkhtmltopdf', url, file])

        self.content_list[index] = file

    def md5(self, string):
        m = hashlib.md5()
        m.update(string.encode('utf-8'))
        return m.hexdigest()


if __name__ == '__main__':
    url_arg = sys.argv[1]
    filename_arg = sys.argv[2]
    Site2PDF(url_arg, filename_arg).run()

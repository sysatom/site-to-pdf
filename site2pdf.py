import sys
from urllib.parse import urlparse, urljoin, urldefrag
import re
import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup
import pdfkit


async def request(url, headers, timeout=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            return await resp.text()


class HtmlGenerator():
    def __init__(self, base_url):
        self.html_start = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">      
"""

        self.title_ele = ""
        self.meta_list = []
        self.body = ""
        self.html_end = """
</body>
</html>
"""
        self.base_url = base_url

    def add_meta_data(self, key, value):
        meta_string = "<meta name={key} content={value}>".format_map({
            'key': key,
            'value': value
        })
        self.meta_list.append(meta_string)

    def add_body(self, body):
        self.body = body

    def srcrepl(self, match):
        "Return the file contents with paths replaced"
        absolutePath = self.base_url
        return "<" + match.group(1) + match.group(2) + "=" + "\"" + absolutePath + match.group(3) + match.group(
            4) + "\"" + ">"

    def relative_to_absolute_path(self, origin_text):
        p = re.compile(r"<(.*?)(src|href)=\"(?!http)(.*?)\"(.*?)>")
        updated_text = p.sub(self.srcrepl, origin_text)
        return updated_text

    def output(self):
        full_html = self.html_start + self.title_ele + "".join(self.meta_list) \
                    + "<body>" + self.body + self.html_end
        return self.relative_to_absolute_path(full_html)


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

        body = ''.join(self.content_list)
        html_g = HtmlGenerator(self.base_url)
        html_g.add_body(body)
        html_text = html_g.output()
        self.write_pdf(html_text, '')

    def collect_urls(self, start_url):
        response = requests.get(start_url, headers=self.headers)
        self.base_url = response.url
        base_o = urlparse(self.base_url)
        start_url = response.url
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
            tasks.append(self.gettext(index, url))
        await asyncio.gather(*tasks)
        print('crawl : all done!')

    async def gettext(self, index, url):
        print('crawling : ', url)
        try:
            metatext = await request(url, self.headers, timeout=30)
        except Exception as e:
            print("retrying : ", url)
            metatext = await request(url, self.headers)

        self.content_list[index] = metatext

    def write_pdf(self, html, css):
        options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'custom-header': [
                ('Accept-Encoding', 'gzip')
            ],
            'cookie': [
                ('cookie-name1', 'cookie-value1'),
                ('cookie-name2', 'cookie-value2'),
            ],
            'outline-depth': 10,
        }
        pdfkit.from_string(html, self.file_name, options=options)


if __name__ == '__main__':
    url = sys.argv[1]
    file = sys.argv[2]
    Site2PDF(url, file).run()

# coding=utf-8
import urllib2
import sys
import os
import re
from collections import OrderedDict

from readability.readability import Document
from bs4 import BeautifulSoup
from ebooklib import epub

reload(sys)
sys.setdefaultencoding('utf-8')  # Needed fore websites that use Unicode


class TableOfContentsError(Exception):
    """
    Useful to raise if TOC not found
    """
    pass


class LightScrap(object):
    """
    Scrapper object which can walk through chapters and grab relevant content
    """

    def __init__(self, title, start_chapter_number, end_chapter_number, url, header=None):
        """
        Instantiates the scrapper with the relevant information like the start URL (url) and how far to walk for
        all the chapters (end_chapter_number)
        :param title: str
        :param start_chapter_number: int
        :param end_chapter_number: int
        :param url: str
        :param header: dict
        :return:
        """
        self.title = title
        self.start_chapter_number = int(start_chapter_number)
        self.end_chapter_number = int(end_chapter_number)
        self.start_url = self.url = url
        self.main_content_div = 'entry-content'
        self.toc = OrderedDict()
        if header is None:
            self.header = {'User-agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.1.5) '
                                         'Gecko/20091102 Firefox/3.5.5'}
        else:
            self.header = header
        if not os.path.exists(self.title):
            os.makedirs(title)

    def visit_url(self, url):
        """
        http://stackoverflow.com/questions/7933417/how-do-i-set-headers-using-pythons-urllib
        :param url: URL to visit
        :return: str
        """
        request = urllib2.Request(url=url, headers=self.header)
        return urllib2.urlopen(request).read()

    def strip_chapter(self, html):
        """
        Strips chapter and gets relevant HTML using Readability
        :param html: str
        :return:
        """
        doc = Document(html)
        if len(doc.summary()) <= 20:
            print 'This page has errors, returning entry-content div raw HTML.'
            content = str(BeautifulSoup(html, 'html.parser').find_all('div', class_=self.main_content_div)[0])
            content = '<html><head><meta charset="utf-8"></head>' + content + '</html>'
            return doc.short_title(), content

        return (doc.short_title(),
                str(doc.summary()).replace('<html>', '<html><head><meta charset="utf-8"></head>'))

    def find_from_toc(self, chapter_number, url):
        """
        Grabs link from table of contents provided the chapter number and TOC URL
        :param chapter_number: int
        :param url: str
        :return:
        """
        chapter_number = str(chapter_number)
        soup = BeautifulSoup(self.visit_url(url), 'html.parser')
        chapter = 'chapter ' + chapter_number
        for link in soup.find_all('a'):
            if chapter in link.text.lower():
                return link.get('href')

    def make_html_toc(self):
        """
        Generates a HTML table of contents (to use with Calibre)
        :return: str
        """
        toc = """<html><html><body><h1>Table of Contents</h1>
        <p style="text-indent:0pt">"""
        chapter_html = '<a href="{0}.html">Chapter {0}</a><br/>'
        for chapter_number in self.toc.keys():
            toc += chapter_html.format(chapter_number)
        toc += '</p></body></html>'
        with open(os.path.join(self.title, self.title + '-toc.html'), 'w+') as f:
            f.write(toc)
        return toc

    def find_toc(self):
        """
        Locate, from the start URL, and return URL of table of contents
        :return:
        """
        soup = BeautifulSoup(self.visit_url(self.start_url), 'html.parser')
        for link in soup.find_all('a'):
            if 'table of contents' in link.text.lower():
                return link.get('href')
        raise TableOfContentsError('Table of contents not found, please specify it.')

    def chapters_walk(self):
        """
        Recursive method to walk from of URL to end
        :return:
        """
        if self.start_chapter_number > self.end_chapter_number:
            return

        self.toc[self.start_chapter_number] = self.url

        # Check if walk is hitting the same url
        if self.url != self.start_url:
            if self.url == self.toc[self.start_chapter_number]:
                # Cycle detected
                self.url = self.find_from_toc(self.start_chapter_number, self.find_toc())

        print 'Fetching chapter ' + str(self.start_chapter_number) + ' ' + self.url

        html = self.visit_url(self.url)
        chapter = self.strip_chapter(html)
        with open(os.path.join(self.title, str(self.start_chapter_number) + '.html'), 'w+') as f:
            f.write(chapter[1])

        # Start walking
        soup = BeautifulSoup(html, 'html.parser')

        toc = ''
        # Find next chapter
        for link in soup.find_all('a'):
            if 'next chapter' in link.text.lower():
                self.start_chapter_number += 1
                self.url = link.get('href')
                return self.chapters_walk()
            if 'table of contents' in link.text.lower():
                toc = link.get('href')
        self.start_chapter_number += 1
        return self.chapters_walk()

    def generate_epub(self):
        """
        Generates a ePub with contents from the chapters_walk()
        :return:
        """
        book = epub.EpubBook()
        book.set_title(self.title)
        chapters = []
        if len(self.toc) < 1:
            self.chapters_walk()
        for chapter in self.toc.keys():
            chapter = str(chapter)
            with open(os.path.join(self.title, chapter + '.html')) as f:
                content = f.read()
            chapter = epub.EpubHtml(title='Chapter ' + chapter,
                                    file_name=chapter + '.xhtml',
                                    content=content)
            book.add_item(chapter)
            chapters.append(chapter)

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav']
        for chapter in chapters:
            book.spine.append(chapter)

        epub.write_epub(os.path.join(self.title, self.title + '.epub'), book, {})

    def toc_walk(self, toc_url):
        """
        Grabs links from table of contents
        :param toc_url: str
        :return:
        """
        self.toc = OrderedDict()
        watered_soup = BeautifulSoup(self.visit_url(toc_url), 'html.parser')
        for i in range(self.start_chapter_number, self.end_chapter_number + 1):
            self.toc[i] = None
        chapter_regex = re.compile(r'[0-9]*(c|C)hapter(\s|\S):(?P<chap_no>[0-9]*)')
        for link in watered_soup.find_all('a'):
            if 'chapter' in link.text.lower():
                found = chapter_regex.search(str(link.text))
                if found is not None:
                    found = found.group('chap_no')
                if found and int(found) in self.toc.keys():
                    self.toc[int(found)] = link.get('href')
                    content = self.strip_chapter(self.visit_url(link.get('href')))
                    with open(os.path.join(self.title, found + '.html'), 'w+') as f:
                            f.write(content[1])


if __name__ == '__main__':
    ls = LightScrap(title='Arcane Emperor',
                    start_chapter_number=1,
                    end_chapter_number=68,
                    url='https://royalroadl.com/fiction/chapter/94620')
    ls.toc_walk('https://royalroadl.com/fiction/8463')
    #ls.chapters_walk()
    # ls.make_html_toc()
    ls.generate_epub()

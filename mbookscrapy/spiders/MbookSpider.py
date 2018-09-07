# -*- coding: utf-8 -*-
from scrapy.spiders import Rule, CrawlSpider
from scrapy.linkextractors import LinkExtractor
from scrapy import Request
from bs4 import BeautifulSoup
from scrapy.shell import inspect_response
from mbookscrapy.items import MbookItem
import re
import json
import pymysql
from mbookscrapy import settings

# 用XPATH解析所有RESPONSE
'''
本程序用来爬取小书屋所有的书籍，目前仅爬取在天翼云盘有存储的电子书
小书屋地址：http://mebook.cc/
爬取后的文件放在setttings.py文件中的指定的目录下，分别爬取电子书图片和电子书
爬取记录分别写文件booklist.json和写数据库表book,数据库建库建表语句在sql文件夹下
支持去重爬取，每次只取曾经未爬取过的书
name:爬虫名子
url_encode: 天翼云盘电子书下载地址
init_sql : 用于爬取URL的去重操作，导入set中，每次取得网页地址后检查，只有不在SET中的地址也爬取
url_set ：去重集合
rules   ：链接抽取规则
'''


class MbookSider(CrawlSpider):
    name = "mbook"
    url_encode = "https://cloud.189.cn/v2/listShareDir.action?shareId=%s&accessCode=%s" \
                 "&verifyCode=%s&orderBy=1&order=ASC&pageNum=1&pageSize=60"
    init_sql = "select book_url from book"
    block_url = "select book_url from book_block_url"
    block_sql_insert = "insert into book_block_url(book_url) values('%s') "
    allowed_domains = [
        "mebook.cc",
        "cloud.189.cn",
    ]
    start_urls = [
        "http://mebook.cc/",
    ]
    url_set = set()
    rules = (

        # 定义 follow= True 才会不断探索新URL
        Rule(LinkExtractor(allow='http://mebook.cc/page/([\d]+)'), callback='parseItem', follow=True),
        Rule(LinkExtractor(allow='http://mebook.cc/'), callback='parseItem'),
        # Rule(LinkExtractor(allow='http://mebook.cc/page/([\d]+)'), callback='parseItem'),


    )

    # 用集合过滤爬取url
    def filter_url(self, value):
        if value in self.url_set:
            return None
        else:
            return value

    # 数据库连接初始化，url排重集合初始化
    def __init__(self, *a, **kw):
        super(MbookSider, self).__init__(*a, **kw)
        self.conn = pymysql.connect(host=settings.DB_HOST, user=settings.DB_USER, passwd=settings.DB_PASSWORD,
                                    charset=settings.DB_CHARSET, port=int(settings.DB_PORT),
                                    database=settings.DB_DBNAME)
        self.cur = self.conn.cursor()
        self.cur.execute(self.init_sql)
        for url in self.cur.fetchall():
            self.url_set.add(url[0])

        self.cur.execute(self.block_url)

        for url in self.cur.fetchall():
            self.url_set.add(url[0])

        self.logger.info('url_set is %s' % str(self.url_set))
        self.logger.info('url_set len %s' % len(self.url_set))

    def parse_start_url(self, response):
        self.parseItem(response)

    # 获取第一个URL
    # def start_requests(self):
    #     yield Request(self.start_urls[0], callback=self.parseItem)

    # 解析每一页：类似于 http://mebook.cc/page/2
    # 将meta信息通过response传递到下一层处理
    # 此层通过BeautifulSoup解析HTML
    def parseItem(self, response):
        soup = BeautifulSoup(response.body)
        lis = soup.select('.list li')

        for li in lis:
            meta = {}
            meta['category'] = li.select('.cat a')[0].string.extract()
            meta['detail_page_url'] = li.select('.link a')[0]['href']
            url = meta['detail_page_url']
            if self.filter_url(url) is not None:
                self.url_set.add(url)
                yield Request(url, callback=self.parse_detail, meta=meta)


    # 解析电子书详细说明页：类似于 http://mebook.cc/20183.html
    # 如果下载地址不为空，将meta信息通过response 带到下一层
    # 此层通过xpath解析HTML
    def parse_detail(self, response):
            url_download = ''
            introduction = ''
            update_date = ''
            metadata = response.meta

            self.logger.info("explain url:  %s" % response.url)

            if len(response.url) > 0:
                try:
                    sql = self.block_sql_insert % response.url
                    self.cur.execute(sql)
                    self.conn.commit()
                except Exception as e:
                    self.logger.info("block_url insert error : " + str(e))

            soup = BeautifulSoup(response.body)
            title = soup.select('#primary h1')[0].string

            for span_text in response.xpath('//div[@id="content"]/h2/following::*/span[contains(@style,"font-family")]/text()').extract():
                introduction = introduction + span_text

            # XPATH 方式提取URL updatedate
            if len(response.xpath('//p[@class="downlink"]')) != 0:
                update_date_list = re.findall(r'\d{4}\.\d{1,2}\.\d{1,2}', response.
                                         xpath('//p[@class="downlink"]/preceding-sibling::*[1]/text()').extract()[0])
                if len(update_date_list) != 0:
                    update_date = update_date_list[0]
                else:
                    update_date = ''

                url_download = response.xpath('//a[@class="downbtn"]/@href').extract()[0]

            if len(response.xpath('//div[@id="content"]/p/img/@src').extract()) != 0:
                metadata['image_url'] = response.xpath('//div[@id="content"]/p/img/@src').extract()[0]
            elif len(response.xpath('//div[@id="content"]/h2/img/@src').extract()) != 0:
                metadata['image_url'] = response.xpath('//div[@id="content"]/h2/img/@src').extract()[0]
            else:
                metadata['image_url'] = ''
            metadata['title'] = title
            metadata['introduction'] = introduction
            metadata['updatedate'] = update_date

            if url_download != '':
                metadata['url'] = url_download
                yield Request(url_download, callback=self.parseDownload, meta=metadata)

    # 解析电子书下载说明页：类似于 http://mebook.cc/download.php?id=20183
    # 如果有天翼云盘的下载地址，则将meta信息通过response 继续传递到下一层
    # 如果没有天翼云盘的下载地址，则直接返回item，由pipeline处理直接写入数据库
    def parseDownload(self, response):
            #密码
            item = MbookItem()
            meta = response.meta
            item['title'] = meta['title']
            item['desc'] = meta['introduction']
            item['update_date'] = meta['updatedate']
            item['category_tag'] = meta['category']
            item['image_url'] = meta['image_url']
            item['detail_page_url'] = meta['detail_page_url']
            item['access_code'] = ''
            item['update_date'] = meta['updatedate']
            downloadpwd = {}
            downloadurl = {}
            try:
                sp = response.xpath('//div[@class="desc"]/p/text()')[-2].extract()
                if sp is None:
                    raise "not down load book"
                sp = sp.replace(u'\xa0', u'')
                sps = sp[sp.find('：')+1:]

                if sps.find('百度网盘密码') != -1:
                    downloadpwd['baidu_pwd'] = sps[sps.find('百度网盘密码') + 7: sps.find('百度网盘密码') + 11]

                if sps.find('天翼云盘密码') != -1:
                    downloadpwd['189_pwd'] = sps[sps.find('天翼云盘密码')+7:sps.find('天翼云盘密码')+11]

                for url in response.xpath('//div[@class="list"]/a/@href').extract():
                    if url.find('baidu') != -1:
                        downloadurl["baidu"] = url.strip()
                    if url.find('ctfile') != -1:
                        downloadurl['ctfile'] = url.strip()
                    if url.find('189') != -1 and url.find('action') == -1:
                        downloadurl['189'] = url.strip()

            finally:
                item['download_pwd'] = downloadpwd
                item['download_url'] = downloadurl
                if downloadpwd.get('189_pwd') is None:
                    item['data'] = ''
                    item['file_name'] = ''
                    yield item
                else:
                    item['access_code'] = downloadpwd['189_pwd']
                    yield Request(str(downloadurl['189']), callback=self.parseyunpan, meta=item, dont_filter=True)

    # 有天翼云盘的，解析天翼网盘提取页面
    # 类似于https://cloud.189.cn/t/y6N7BfmiUNri 提取码0105
    def parseyunpan(self, response):
        item = response.meta
        share_id = re.findall(r'_shareId = \'(\d+)', response.xpath('//script')[-3].extract())[0]
        verify_code = re.findall(r'_verifyCode = \'(\d+)', response.xpath('//script')[-3].extract())[0]
        url = self.url_encode % (share_id, item['access_code'], verify_code)
        yield Request(url.strip(), callback=self.parsedownpage, meta=item, dont_filter=True)

    # 上个页面获取share id 验证码后，处理返回的JSON报文
    # 给到pipeline 处理
    def parsedownpage(self, response):
        item = response.meta
        book_down = []
        res_dict = json.loads(str(response.body, 'utf-8'))

        if res_dict.get('data') is not None:
            for book in res_dict.get('data'):
                book_down.append(book)
            item['data'] = book_down
        else:
            item['data'] = ''

        if res_dict.get('path') is not None:
            item['file_name'] = res_dict.get('path')[0]['fileName']
        else:
            item['file_name'] = ''
        yield item

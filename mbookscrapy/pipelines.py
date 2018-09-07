# -*- coding: utf-8 -*-
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json
from mbookscrapy import settings
import os
import uuid
import requests
import logging
import pymysql
import time
'''
数据库处理的pipeline
接受spider返回的ITEM
1.写booklist.json文件，内容较全
2.有天翼云下载电子书的，下载天翼云下载电子书到电子书名的文件夹下
3.下载电子书对应图片
4.关闭数据库连接，关闭文件

直接插入 book detail ，已测试OK
'''


class MbookscrapyDatabasePipeline(object):
    base_dir = '.'
    pic_dir = 'pic'
    file_name_out = 'booklist.json'
    book_dir = 'ebook'
    table_name = 'book'
    block_sql_insert = "insert into book_block_url(book_url) values('%s') "
    sql_insert = "INSERT INTO BOOK(catagory_tag,book_url,book_name,book_desc,down_url,down_pwd,file_path,image_path," \
                 "download_flag,update_date) values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')"

    sql_insert_bookdetail = "INSERT INTO BOOK_DETAIL(catagory_tag,catagory_tag_main,catagory_tag_side,update_date_yyyy," \
                            "update_date_mm,update_date_dd,book_url,book_name,book_desc," \
                            "down_url,down_pwd,file_path,image_path,download_flag,update_date)" \
                            "values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')"

    def __init__(self):
        self.file = open('%s/%s' % (settings.IMAGES_STORE if settings.IMAGES_STORE is not None else self.base_dir,
                                    self.file_name_out), 'a', encoding='utf-8')
        # self.file.write('[')
        self.dir_path_pic = '%s/%s' % (settings.IMAGES_STORE if settings.IMAGES_STORE is not None
                                       else self.base_dir, self.pic_dir)
        self.dir_path_book = '%s/%s' % (settings.IMAGES_STORE if settings.IMAGES_STORE is not None
                                        else self.base_dir, self.book_dir)
        logging.info('dir_path is :%s ' % self.dir_path_pic)

        if not os.path.exists(self.dir_path_pic):
            os.mkdir(self.dir_path_pic)

        if not os.path.exists(self.dir_path_book):
            os.mkdir(self.dir_path_book)

        self.conn = pymysql.connect(host=settings.DB_HOST, user=settings.DB_USER, passwd=settings.DB_PASSWORD,
                                    charset=settings.DB_CHARSET, port=int(settings.DB_PORT),
                                    database=settings.DB_DBNAME)
        # self.conn = pymysql.connect(host='localhost', user='bookexec', passwd='bookexec',
        #                             charset='utf8', port=3306, database='mebook')
        self.cur = self.conn.cursor()

    def process_item(self, item, spider):
        file_name_pic = ''
        book_path_file = ''
        download_flag = 'N'

        # 有天翼云下载电子书
        if item['data'] != '':
            books = item['data']
            download_flag = 'Y'
            logging.info('file_name is : %s' % item['file_name'])

            book_path = '%s/%s' % (self.dir_path_book, item['file_name'])
            book_path_file = book_path
            if not os.path.exists(book_path):
                os.mkdir(book_path)

        try:
            for book in books:
                url = 'http:' + book['downloadUrl'].replace('\/', "")
                file_name = '%s/%s' % (book_path, book['fileName'])
                self.write_file(url, file_name)
        except Exception as e:
            try:
                sql = self.block_sql_insert % (item['book_url'])
                self.cur.execute(sql)
                self.conn.commit()
            except Exception as e:
                print(" db error")

            print("url key error: %s " % (item['file_name']))

        # 下载电子书图片
        pic_url = item['image_url']
        file_name_al = str(uuid.uuid1()) + pic_url[-4:]
        file_name = '%s/%s' % (self.dir_path_pic, file_name_al)
        file_name_pic = file_name

        if len(pic_url.strip()) != 0:
            with open(file_name, 'wb') as handle:
                response = requests.get(pic_url, stream=True)
                for block in response.iter_content(1024):
                    if not block:
                        break
                    handle.write(block)
        else:
            file_name_pic = ''

        item['image_path'] = file_name_pic
        line = json.dumps(dict(item), ensure_ascii=False) + "\n"
        # self.file.write(line + ',')
        self.file.write(line)
        sql = ''
        if item['update_date'] != '':
            updateyyyy, updatemonth, updateday = item['update_date'].split('.')
        else:
            updateyyyy = time.strftime('%Y', time.localtime(time.time()))
            updatemonth = time.strftime('%m', time.localtime(time.time()))
            updateday = time.strftime('%d', time.localtime(time.time()))

        catamain, catasub = self.cataTransfer(item['category_tag'])
        try:
            sql = self.sql_insert_bookdetail % (item['category_tag'], catamain, catasub, updateyyyy, updatemonth,
                                                updateday, item['detail_page_url'], item['title'].replace('\r\n', ''),
                                     item['desc'], json.dumps(dict(item['download_url']), ensure_ascii=False),
                                     json.dumps(dict(item['download_pwd']), ensure_ascii=False),
                                     book_path_file, file_name_pic, download_flag, item['update_date'])

            self.cur.execute(sql)
            self.conn.commit()
        except Exception():
            raise Exception('sql process error')
        finally:
            return item

        return item

    def close_spider(self, spider):
        self.file.seek(self.file.tell() - 1)
        self.file.truncate()
        # self.file.write(']')
        self.file.close()
        self.cur.close()
        self.conn.close()

    def write_file(self, url, file_name):
        with open(file_name, 'wb') as handle:
            response = requests.get(url, stream=True)
            for block in response.iter_content(1024):
                if not block:
                    break
                handle.write(block)

    def cataTransfer(self, cata):
        switch = {
            '军事科学·历史地理': ('CXXS', 'JSKX'),
            '多看专区': ('DKZQ', 'DKZQ'),
            'kindle人全站打包': ('HJZY', 'KRDB'),
            '中亚官方合集资源下载': ('HJZY', 'ZYHJ'),
            '畅销小说': ('CXXS', 'CXXS'),
            '官场商战·人生百态': ('CXXS', 'GCSZ'),
            '人物传记·旅行见闻': ('CXXS', 'RWZJ'),
            '其他站点合集资源下载': ('HJZY', 'QTHJ'),
            '武侠玄幻·穿越言情': ('WLXS', 'CYYQ'),
            '电纸书工具': ('SJGJ', 'SJGJ'),
            '现代文学·励志鸡汤': ('CXXS', 'XDWX'),
            '原版书籍': ('YBSJ', 'YBSJ'),
            '工具书': ('GJS', 'GJS'),
            '网络小说': ('WLXS', 'WLXS'),
            '生活养生·运动健身': ('CXXS', 'SHYS'),
            'kindle漫画': ('MH', 'MH'),
            '杂志·期刊': ('ZZQK', 'ZZQK'),
            'office办公': ('GJS', 'OFBG'),
            '科幻奇幻·西方异世': ('WLXS', 'KHQH'),
            '历史架空·热血战争': ('WLXS', 'LSJK'),
            '悬疑恐怖·穿越重生': ('WLXS', 'XQKB'),
            '官场商战·阴谋阳谋': ('CXXS', 'GCSZ'),
            '武侠玄幻·仙侠修真': ('WLXS', 'XXXZ'),
            '合集资源': ('HJZY', 'HJZY'),
            '书评': ('SP', 'SP'),
            '甲骨文系列丛书': ('HJZY', 'JGW'),
            '轻小说': ('QXS', 'QXS')
        }
        return switch.get(cata, ('QTSJ', 'QTSJ'))

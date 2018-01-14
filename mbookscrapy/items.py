# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


# 下载文件详细信息
class MbookItem(Item):
    # 电子书标题
    title = Field()
    # 电子书简介
    desc = Field()
    # 电子书封面地址
    image_url = Field()
    # 电子书封面图片文件
    image_path = Field()
    # 小书屋相关电子书的更新日期
    update_date = Field()
    # 下载电子书的URL 包含各种云盘的地址
    download_url = Field()
    # 下载电子书的云盘分享密码
    download_pwd = Field()
    # 电子书分类
    category_tag = Field()
    # 电子书详细信息地址
    detail_page_url = Field()
    # 天翼云盘的下载信息
    data = Field()
    # 电子书名
    file_name = Field()
    # 天翼云盘分享受密码
    access_code = Field()





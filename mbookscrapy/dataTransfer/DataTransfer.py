import pymysql
from mbookscrapy import settings

# bookInquireSql = "SELECT seqno,catagory_tag,enter_date from book_detail"
bookInquireSql = "SELECT seqno,catagory_tag,enter_date,update_date from book_detail where update_date_yyyy is null"
bookdetailInsertSql = "update book_detail set catagory_tag_main='%s',catagory_tag_side='%s',update_date_yyyy='%s'," \
                      "update_date_mm='%s',update_date_dd='%s' where seqno='%s'"

conn = pymysql.connect(host=settings.DB_HOST, user=settings.DB_USER, passwd=settings.DB_PASSWORD,
                            charset=settings.DB_CHARSET, port=int(settings.DB_PORT),
                            database=settings.DB_DBNAME)

cur = conn.cursor()
cur.execute(bookInquireSql)


def cataTransfer(cata):
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

for book in cur.fetchall():
    seqno = book[0]
    print(seqno)
    cata = book[1]

    if book[3] != '':
        updateyyyy, updatemonth, updateday = book[3].split('.')
    else:
        updateyyyy = book[2].year
        updatemonth = book[2].month
        updateday = book[2].day

    catamain, catasub = cataTransfer(cata)

    sql = bookdetailInsertSql % (catamain, catasub, updateyyyy, updatemonth, updateday, seqno)
    cur.execute(sql)
    conn.commit()




cur.close()
conn.close()


from scrapy import cmdline

name = 'mbook'
cmd = 'scrapy crawl %s' % name

cmdline.execute(cmd.split())

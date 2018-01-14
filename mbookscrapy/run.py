from scrapy import cmdline

name = 'mbook7'
cmd = 'scrapy crawl %s' % name

cmdline.execute(cmd.split())

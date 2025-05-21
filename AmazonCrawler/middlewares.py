# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class AmazoncrawlerSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class AmazoncrawlerDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)

# 不同国家cookies切换中间件
class RegionCookiesMiddleware:
    """根据 region 自动添加对应 cookies"""

    REGION_COOKIES = {
        "US": {
            'session-id': '142-0777523-8131625',
            'lc-main': 'en_US',
            'ubid-main': '135-0851440-4909440',
        },
        "UK": {
            'session-id': '261-5340826-5234657',
            'lc-acbuk': 'en_GB',
            'ubid-acbuk': '260-5838401-4465113',
        },
        "DE": {
            'session-id': '257-2217119-9542653',
            'lc-acbde': 'en_GB',
            'ubid-acbde': '258-8925858-0888936',

        },
        "JP": {
            'session-id': '357-4127060-6127553',
            'ubid-acbjp': '357-3446367-7551403',
        },
    }

    def process_request(self, request, spider):
        """根据请求中的 meta['region'] 为请求添加 cookies"""
        region = request.meta.get('region')
        if region and region in self.REGION_COOKIES:
            request.cookies.update(self.REGION_COOKIES[region])
            spider.logger.debug(f"[Cookies] 为 region={region} 添加 cookies")
        else:
            spider.logger.warning(f"[Cookies] 未知或缺失 region：{region}")
        return None




from urllib.parse import urlencode

import scrapy

from AmazonCrawler.items import SellerAsinItem
from AmazonCrawler.sql.seller_crawler import AmazonSellerCrawlerDB


class SellerAsinSpider(scrapy.Spider):
    """
    SellerAsinSpider 是一个用于抓取亚马逊特定卖家所售商品 ASIN 的 Scrapy 爬虫。

    该爬虫支持多个站点（美国、英国、德国、日本），通过传入卖家ID构造查询URL，
    然后解析商品列表页，提取商品ASIN并分页抓取完整商品列表。
    """
    name = "seller_asin"

    # 允许爬取的域名列表，用于防止爬虫跳转到非目标站点
    allowed_domains = [
        "www.amazon.com",
        "www.amazon.co.uk",
        "www.amazon.de",
        "www.amazon.co.jp",
    ]

    # 地区与对应亚马逊站点URL的映射关系
    domain_mapping = {
        "US": "https://www.amazon.com/s?",    # 美国站
        "UK": "https://www.amazon.co.uk/s?",  # 英国站
        "JP": "https://www.amazon.co.jp/s?",  # 日本站
        "DE": "https://www.amazon.de/s?",     # 德国站
    }

    def __init__(self, region=None, seller_all=None, *args, **kwargs):
        """
        初始化爬虫，设置目标区域和卖家列表。

        参数:
            region (str): 地区缩写（US、UK、JP、DE），指定抓取哪个亚马逊站点。
            *args: 其他位置参数。
            **kwargs: 其他关键字参数。
        """
        super().__init__(*args, **kwargs)

        self.region = region.upper() if region else None
        if not self.region or self.region not in self.domain_mapping:
            raise ValueError(
                f"无效的地区缩写：{self.region}。有效的地区包括：{', '.join(self.domain_mapping.keys())}"
            )

        # # 卖家ID列表，可在此扩展多个卖家ID
        # self.seller_all = [
        #     'AC7TDJNE5BJJD',  # 示例卖家ID
        # ]
        if isinstance(seller_all, str):
            self.asin_all = [seller_all]
        if seller_all is None:
            db = AmazonSellerCrawlerDB()
            seller_all = db.get_sellers_to_crawl(region=self.region)
        self.seller_all = seller_all if seller_all else []

        if not self.seller_all:
            raise ValueError("必须提供至少一个卖家ID")

    def start_requests(self):
        """
        构建初始请求，每个卖家生成一个请求，访问其商品列表页面。
        """
        for seller in self.seller_all:
            params = {
                'me': seller,               # 卖家ID参数
                'i': 'merchant-items',      # 商品类别设定为“卖家商品”
            }
            url = self.domain_mapping[self.region] + urlencode(params)
            yield scrapy.Request(
                url,
                meta={'seller_id': seller,
                      'region':self.region},  # 将卖家ID通过 meta 传递
                callback=self.parse,         # 指定回调函数
            )

    def parse(self, response, **kwargs):
        """
        解析搜索结果页面，提取商品ASIN并翻页抓取。

        参数:
            response (scrapy.http.Response): Scrapy响应对象，包含HTML源码等信息。
        """
        seller_id = response.meta['seller_id']

        # 遍历商品容器
        for product in response.css('div.s-main-slot div.s-result-item').getall():
            # 提取商品详情页链接，寻找包含 '/dp/' 的链接
            asin_link = scrapy.Selector(text=product).css('a.a-link-normal::attr(href)').get()
            if asin_link and '/dp/' in asin_link:
                # 从URL中提取ASIN
                asin = asin_link.split('/dp/')[1].split('/')[0]
                item = SellerAsinItem()
                item['seller_id'] = seller_id
                item['asin'] = asin
                item['region'] = self.region
                yield item

        # 检查是否有下一页链接，并递归抓取
        next_page = response.css('a.s-pagination-next::attr(href)').get()
        if next_page:
            next_page_url = response.urljoin(next_page)
            yield scrapy.Request(
                next_page_url,
                meta={'seller_id': seller_id,
                      'region':self.region},
                callback=self.parse,
            )

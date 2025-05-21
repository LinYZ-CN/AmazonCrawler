import re
from urllib.parse import urlencode
from typing import Set, Generator, Optional
import scrapy
from scrapy.http import Response, Request
from AmazonCrawler.items import AsinSellerItem
from AmazonCrawler.sql.seller_crawler import AmazonSellerCrawlerDB


class SellerShopSpider(scrapy.Spider):
    """用于爬取亚马逊商品页面上卖家信息的Scrapy爬虫

    该爬虫从不同地区(美国、英国、日本、德国)的亚马逊商品页面提取卖家详细信息
    (名称、ID、配送信息)。它可以处理置顶报价和跟卖报价，并支持分页爬取。

    属性:
        name (str): 爬虫的唯一标识符
        allowed_domains (list[str]): 允许爬取的域名列表
        domain_mapping (dict): 地区代码到亚马逊域名的映射
        sellers (set[str]): 已处理的卖家ID集合(用于去重)
        asin_all (list[str]): 要爬取的ASIN列表
        region (str): 目标地区代码(US/UK/JP/DE)
    """

    name = "seller_shop"

    # 允许爬取的域名列表
    allowed_domains = [
        "www.amazon.com",
        "www.amazon.co.uk",
        "www.amazon.de",
        "www.amazon.co.jp",
    ]

    # 地区代码到亚马逊URL的映射
    domain_mapping = {
        "US": "https://www.amazon.com/gp/product/ajax/ref=dp_aod_NEW_mbc?",  # 美国站
        "UK": "https://www.amazon.co.uk/gp/product/ajax/ref=dp_aod_NEW_mbc?",  # 英国站
        "JP": "https://www.amazon.co.jp/gp/product/ajax/ref=dp_aod_NEW_mbc?",  # 日本站
        "DE": "https://www.amazon.de/gp/product/ajax/ref=dp_aod_NEW_mbc?",  # 德国站
    }

    # custom_settings = {
    #         'DOWNLOAD_DELAY': 3,  # 每次请求之间延迟3秒（适当调大更稳）
    #         'CONCURRENT_REQUESTS': 1,  # 全局最多1个并发请求
    #         'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # 每个域名最多1个并发请求
    #         'CONCURRENT_REQUESTS_PER_IP': 1,  # 每个IP最多1个请求（对抗Cloudflare/CDN）
    #         'RETRY_TIMES': 5,  # 失败重试次数
    #         'AUTOTHROTTLE_ENABLED': False,  # 禁用动态限速机制，完全靠固定延时
    # }

    def __init__(self, region: str = None,asin_all=None, *args, **kwargs) -> None:
        """初始化爬虫实例

        Args:
            region: 地区代码(US/UK/JP/DE)，指定要爬取的亚马逊站点
            *args: 可变长度参数列表
            **kwargs: 任意关键字参数

        Raises:
            ValueError: 如果未提供region参数或region无效
        """
        super().__init__(*args, **kwargs)

        self.region = region.upper() if region else None
        if not self.region or self.region not in self.domain_mapping:
            raise ValueError(f"无效的地区缩写：{region}。有效的地区包括：{', '.join(self.domain_mapping.keys())}")
        if isinstance(asin_all, str):
            self.asin_all = [asin_all]  # 字符串转单元素列表
        if asin_all is None:
            db = AmazonSellerCrawlerDB()
            asin_all = db.get_products_to_crawl(region=self.region)
            self.asin_all = asin_all if asin_all else []
        # print(f"<UNK>{self.asin_all}")
        # 用于存储已处理的卖家ID(避免重复)
        self.sellers: Set[str] = set()
        # 要爬取的ASIN列表(示例ASIN)
        # self.asin_all = ['B0DKMCJBHK']

        if not self.asin_all:
            raise ValueError("必须提供至少一个ASIN")

    def start_requests(self) -> Generator[Request, None, None]:
        """生成初始请求

        为每个ASIN生成对应的商品页面请求

        Yields:
            scrapy.Request: 每个ASIN商品页面的请求对象
        """
        for asin in self.asin_all:
            params = {
                'asin': asin,
                'pc': 'dp',
                'experienceId': 'aodAjaxMain',
                'pageno': '1',
            }
            url = self.domain_mapping[self.region] + urlencode(params)
            yield scrapy.Request(
                url=url,
                method="GET",
                callback=self.parse,
                meta={'asin': asin,
                      'region':self.region},
            )

    def parse(self, response: Response, **kwargs):
        """解析商品页面响应，提取卖家信息

        Args:
            response: 商品页面的响应对象
            **kwargs: 额外参数

        Yields:
            对于新卖家返回SellerItem字典，对于分页返回Request对象
        """
        current_sellers: Set[str] = set()  # 当前页找到的卖家
        asin = response.meta['asin']  # 从meta中获取ASIN

        # 处理置顶(黄金购物车)卖家
        top_seller = response.css("#aod-pinned-offer-additional-content")
        shop_href = top_seller.css('.a-size-small.a-link-normal::attr(href)').get()
        delivery = top_seller.css('.a-size-small.a-color-base::text').get()
        seller_id = seller_id_extract(shop_href) if shop_href else None

        yield from self._process_seller_info(asin, current_sellers, delivery, seller_id)

        # 处理跟卖卖家
        for offer_html in response.css("#aod-offer").getall():
            offer_selector = scrapy.Selector(text=offer_html)
            shop_href = offer_selector.css('#aod-offer-soldBy').css(
                '.a-size-small.a-link-normal::attr(href)').get()
            delivery = offer_selector.css('#aod-offer-shipsFrom').css(
                '.a-size-small.a-color-base::text').get()
            seller_id = seller_id_extract(shop_href) if shop_href else None

            yield from self._process_seller_info(asin, current_sellers, delivery, seller_id)

        # 如果有新卖家，则处理分页
        if current_sellers:
            current_page = int(response.url.split("pageno=")[-1])
            next_page_url = response.url.replace(
                f"pageno={current_page}",
                f"pageno={current_page + 1}"
            )
            yield scrapy.Request(next_page_url, callback=self.parse, meta={'asin': asin,'region':self.region})

    def _process_seller_info(
            self,
            asin: str,
            current_sellers: Set[str],
            delivery: Optional[str],
            seller_id: Optional[str]
    ):
        """处理卖家信息，如果是新卖家则生成数据项

        Args:
            asin: 商品ASIN
            current_sellers: 当前页找到的卖家集合
            delivery: 配送信息文本
            seller_id: 卖家ID

        Yields:
            如果是新卖家，返回SellerItem字典
        """
        if seller_id and seller_id not in self.sellers:
            self.sellers.add(seller_id)  # 添加到全局集合
            current_sellers.add(seller_id)  # 添加到当前页集合
            item = AsinSellerItem()
            item['asin'] = asin
            item['seller_id'] = seller_id
            item['delivery'] = delivery
            item['region'] = self.region.upper()
            yield item


def seller_id_extract(href: str) -> Optional[str]:
    """从亚马逊卖家链接中提取卖家ID

    Args:
        href: 包含卖家信息的URL字符串

    Returns:
        提取到的卖家ID，如果未找到则返回None
    """
    match = re.search(r'seller=(\w+)', href)
    return match.group(1) if match else None
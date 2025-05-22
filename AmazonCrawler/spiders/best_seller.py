"""亚马逊畅销商品爬虫

此爬虫用于抓取亚马逊各站点(美国、英国、德国、日本)的畅销商品列表数据。

主要功能:
- 支持多个亚马逊国际站点
- 自动识别URL所属国家/地区
- 自动翻页抓取(最多400页)
- 提取商品ASIN、品牌、价格、销量等关键信息
- 处理多语言和不同货币格式

使用方式:
scrapy crawl best_seller -a url="亚马逊畅销商品列表URL"

注意事项:
1. URL必须属于允许的域名(amazon.com/.co.uk/.de/.co.jp)
2. 需要提供完整的URL(可带或不带https://)
"""

import re
import scrapy
from urllib.parse import urlparse
from AmazonCrawler.items import ProductItem


class BestSellerSpider(scrapy.Spider):
    """亚马逊畅销商品爬虫主类

    继承自scrapy.Spider，负责处理请求和解析响应。
    """

    name = "best_seller"  # 爬虫名称
    allowed_domains = [
        "amazon.com",    # 美国站
        "amazon.co.uk",  # 英国站
        "amazon.de",    # 德国站
        "amazon.co.jp", # 日本站
    ]

    def get_region_from_url(self, url):
        """根据URL提取国家/地区代码

        Args:
            url (str): 亚马逊商品列表URL

        Returns:
            str: 国家/地区代码(US/UK/DE/JP)，无法识别则返回None
        """
        domain_to_region = {
            "amazon.com": "US",  # 美国
            "amazon.co.uk": "UK",  # 英国
            "amazon.de": "DE",  # 德国
            "amazon.co.jp": "JP",  # 日本
        }

        # 使用urllib解析域名
        domain = urlparse(url).netloc
        for amazon_domain, region in domain_to_region.items():
            if amazon_domain in domain:
                return region
        return None

    def __init__(self, url=None, *args, **kwargs):
        """爬虫初始化

        Args:
            url (str): 亚马逊畅销商品列表URL
        """
        super(BestSellerSpider, self).__init__(*args, **kwargs)
        if not url:
            raise ValueError("请输入亚马逊畅销商品列表的URL")

        # 标准化URL（确保有https://开头）
        if not url.startswith('http'):
            url = 'https://' + url

        # 验证URL是否属于允许的域名
        if not any(domain in url for domain in self.allowed_domains):
            raise ValueError(f"URL必须属于以下域名之一: {', '.join(self.allowed_domains)}")

        self.url = url

    def start_requests(self):
        """生成初始请求

        根据输入URL生成翻页请求(最多400页)
        """
        region = self.get_region_from_url(self.url)
        if not region:
            self.logger.error(f"无法从URL {self.url} 中识别地区")
            return

        for page in range(1, 401):  # 翻页400页
            # 确保URL格式正确（移除可能存在的重复参数）
            base_url = self.url.split('&')[0]  # 获取基础URL
            yield scrapy.Request(
                url=f"{base_url}&page={page}&fs=true",
                meta={"region": region},
                callback=self.parse,
            )

    def parse(self, response, **kwargs):
        """解析商品列表页

        Args:
            response: scrapy响应对象
        """
        region = response.meta['region']
        product_divs = response.xpath('//div[@role="listitem"]')

        for product in product_divs:
            item = ProductItem()
            item['asin'] = product.attrib.get('data-asin')  # 商品ASIN
            item['brand'] = product.xpath('.//span[@class="a-size-base-plus a-color-base"]/text()').get()  # 品牌

            price = product.xpath('.//span[@class="a-offscreen"]/text()').get()
            item['price'] = price_extract(price) if price else None  # 价格

            sale = product.xpath('.//span[@class="a-size-base a-color-secondary"]/text()').get()
            item['sale'] = sale_extract(sale) if sale else None  # 销量

            item['region'] = region  # 地区
            yield item


def sale_extract(string):
    """从字符串中提取销量数字

    支持处理多语言销量描述和不同单位(k/千)

    Args:
        string (str): 包含销量信息的原始字符串

    Returns:
        int: 提取并转换后的销量数字，无法提取则返回None
    """
    if string is None:
        return None
    # 匹配不同语言的销量描述(英文/日文等)
    pattern = r'(\d+(?:[,.]?\d+)?)([Kk]?)\+?\s*(?:点)?(?:以上)?(?:\s*)?(?:購入されました|bought in past month|過去.*?か月)'
    match = re.search(pattern, string)
    if match:
        num = float(match.group(1).replace(',', ''))  # 处理千位分隔符
        unit = match.group(2).lower()
        if unit == 'k':  # 处理k单位(千)
            num *= 1000
        return int(num)
    return None


def price_extract(string):
    """从字符串中提取价格数字

    支持处理不同货币格式和千位分隔符

    Args:
        string (str): 包含价格信息的原始字符串

    Returns:
        float: 提取并转换后的价格数字，无法提取则返回None
    """
    if not string:
        return None
    # 匹配价格数字(支持负数、小数和千位分隔符)
    match = re.search(r'-?\d+(?:\.\d+)?', string.replace(',', ''))
    price = float(match.group(0))
    return price
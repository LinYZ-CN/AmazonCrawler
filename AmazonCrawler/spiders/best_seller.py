import re
import scrapy
from urllib.parse import urlparse
from AmazonCrawler.items import ProductItem


class BestSellerSpider(scrapy.Spider):
    name = "best_seller"
    allowed_domains = [
        "amazon.com",
        "amazon.co.uk",
        "amazon.de",
        "amazon.co.jp",
    ]

    def get_region_from_url(self, url):
        """根据URL提取国家/地区代码"""
        domain_to_region = {
            "amazon.com": "US",
            "amazon.co.uk": "UK",
            "amazon.de": "DE",
            "amazon.co.jp": "JP",
        }

        # 使用urllib解析域名
        domain = urlparse(url).netloc
        for amazon_domain, region in domain_to_region.items():
            if amazon_domain in domain:
                return region
        return None

    def __init__(self, url=None, *args, **kwargs):
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
        region = response.meta['region']
        product_divs = response.xpath('//div[@role="listitem"]')

        for product in product_divs:
            item = ProductItem()
            item['asin'] = product.attrib.get('data-asin')
            item['brand'] = product.xpath('.//span[@class="a-size-base-plus a-color-base"]/text()').get()

            price = product.xpath('.//span[@class="a-offscreen"]/text()').get()
            item['price'] = price_extract(price) if price else None

            sale = product.xpath('.//span[@class="a-size-base a-color-secondary"]/text()').get()
            item['sale'] = sale_extract(sale) if sale else None

            item['region'] = region
            yield item



def sale_extract(string):
    """从字符串中提取销量数字

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
        num = float(match.group(1).replace(',', ''))  # 千位分隔符
        unit = match.group(2).lower()
        if unit == 'k':  # 处理k单位(千)
            num *= 1000
        return int(num)
    return None


def price_extract(string):
    """从字符串中提取价格数字

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
import re
from urllib.parse import urlencode
import scrapy
from AmazonCrawler.items import ProductItem
from AmazonCrawler.sql.amazon_product import AmazonProduct


class AmazonBrandSpider(scrapy.Spider):
    """亚马逊品牌产品爬虫

    用于爬取亚马逊不同地区站点上指定ASIN码的商品信息
    """
    name = "product_info"  # 爬虫名称

    # 允许爬取的域名列表
    allowed_domains = [
        "www.amazon.com",
        "www.amazon.co.uk",
        "www.amazon.de",
        "www.amazon.co.jp",
    ]

    # 地区与亚马逊站点URL的映射关系
    domain_mapping = {
        "US": "https://www.amazon.com/s?",  # 美国站
        "UK": "https://www.amazon.co.uk/s?",  # 英国站
        "JP": "https://www.amazon.co.jp/s?",  # 日本站
        "DE": "https://www.amazon.de/s?",  # 德国站
    }


    def __init__(self, *args,region=None, **kwargs):
        """初始化爬虫

        Args:
            region (str): 地区代码(US/UK/JP/DE)，用于确定爬取哪个亚马逊站点
            *args: 可变参数
            **kwargs: 关键字参数
        """
        super().__init__(*args, **kwargs)

        self.region = region.upper() if region else None
        if not self.region or self.region not in self.domain_mapping:
            raise ValueError(f"无效的地区缩写：{region}。有效的地区包括：{', '.join(self.domain_mapping.keys())}")

        product_db = AmazonProduct()
        migrated_count = product_db.migrate_seller_products()
        print(f"共迁移了 {migrated_count} 条新记录")

        self.asin_all = product_db.get_asin_by_region(self.region)

        # # 要爬取的ASIN列表
        # self.asin_all = [
        #     'B0D5V5MFSZ',  # 示例ASIN
        # ]

    def start_requests(self):
        """生成初始请求

        为每个ASIN生成对应的搜索URL请求
        """
        for asin in self.asin_all:
            params = {
                'k': asin,  # 搜索关键词
                'i': 'fashion',  # 商品类别
            }
            url = self.domain_mapping[self.region] + urlencode(params)
            yield scrapy.Request(
                url=url,
                method="GET",
                callback=self.parse,
                meta={'asin': asin,
                      'region':self.region},  # 传递ASIN到回调函数
            )

    def parse(self, response, **kwargs):
        """解析商品页面

        Args:
            response: 网页响应对象
            **kwargs: 其他关键字参数

        Returns:
            ProductItem: 包含商品信息的Item对象
        """
        item = ProductItem()
        asin = response.meta['asin']  # 从meta中获取ASIN
        region = response.meta['region']
        # 使用ASIN定位商品div
        product_div = response.xpath(f'//div[@data-asin="{asin}"]')

        # 提取品牌信息
        brand = product_div.xpath('.//span[@class="a-size-base-plus a-color-base"]/text()').extract_first()
        # 提取价格信息
        price = product_div.xpath('.//span[@class="a-offscreen"]/text()').extract_first()
        # 提取销量信息
        sale = product_div.xpath('.//span[@class="a-size-base a-color-secondary"]/text()').extract_first()

        # 填充Item字段
        item['asin'] = asin
        item['brand'] = brand
        item['price'] = price_extract(price) if price else None  # 提取并处理价格
        item['sale'] = sale_extract(sale) if sale else None  # 提取并处理销量
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
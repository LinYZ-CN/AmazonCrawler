import json
import scrapy

from AmazonCrawler.items import ProductItem
from AmazonCrawler.sql.amazon_brand import AmazonBrand


def get_payload(brand):
    """构造 POST 请求所需的 payload 数据"""
    return {
        "DISP_ID": "S0000",
        "SEARCH_TYPE": "1",
        "SEARCH_TARGET_TYPE": {"APP_REG_INFO": 1, "BUL": 0},
        "SIMPLE_SEARCH_DISP": {
            "AUTO_NARROW_FLG": 1,
            "SEARCH_COND": [{"NUM_TYPE": [], "KEYWD": brand}],
            "SEARCH_OPTN": {
                "FILTER_INFO": {
                    "FILTER_MAXIMUM_CNT_PER_APP_Y_BY": 10,
                    "FILTER_MAXIMUM_CNT_APP_TYPE": 10,
                    "FILTER_MAXIMUM_CNT_PER_DIVISION": 10,
                    "FILTER_MAXIMUM_CNT_TRADEMARK_TYPE": 10,
                }
            },
        },
        "SEARCH_RSLT_MAX_CNT": 3000,
        "NUM_LST_MAX_CNT": 3000,
        "INPUT_NUM_LST": [],
        "SORT_INFO": {"SORT_ORDER": 0},
    }


class JpoBrandSpider(scrapy.Spider):
    name = "jpo_brand"
    allowed_domains = ["www.j-platpat.inpit.go.jp"]
    start_urls = ["https://www.j-platpat.inpit.go.jp/app/tradeapi/wst0303"]
    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,

    }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = AmazonBrand()
        self.brand_all = self.db.get_brands_by_region(region="JP")
    def start_requests(self):
        """启动请求，发送 POST 请求并传入指定的 JSON 数据"""
        for brand in self.brand_all:
            payload = get_payload(brand)
            yield scrapy.Request(
                url=self.start_urls[0],
                method="POST",
                body=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                callback=self.parse,
                errback=lambda failure: self.error_handler(failure),# 增加错误处理的回调
                dont_filter=True,
                meta={'brand': brand},
            )

    def parse(self, response, **kwargs):
        """
        解析响应数据
        :param response: scrapy.HTTPResponse 对象
        """
        item = ProductItem()
        brand = response.meta['brand']
        try:
            result = json.loads(response.text)
            search_hit_count = result["RSLT_INFO"]["SEARCH_HIT_CNT"]
            if int(search_hit_count) == 0:
                item['brand'] = brand
                item['region'] = 'JP'
                item['status'] = 0
                yield item
            else:
                item['brand'] = brand
                item['region'] = 'JP'
                item['status'] = 1
                yield item
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失败: {e}")
        except Exception as e:
            self.logger.error(f"发生未知错误: {e}")

    def error_handler(self, failure):
        """
        请求错误处理函数
        :param failure: twisted.failure.Failure 对象
        """
        self.logger.error(f"请求失败，错误信息: {failure.value}")
        self.logger.error(f"请求失败的 URL: {failure.request.url}")

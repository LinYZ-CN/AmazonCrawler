import json
import scrapy
from AmazonCrawler.items import ProductItem
from AmazonCrawler.sql.amazon_brand import AmazonBrand


class TmBrandSpider(scrapy.Spider):
    name = "tm_brand"
    allowed_domains = ["www.tmdn.org"]
    start_urls = ["https://www.tmdn.org/tmview/api/search/results"]

    COUNTRY_JSON_TEMPLATES = {
        "UK": {
            "page": "1",
            "pageSize": "30",
            "criteria": "I",
            "offices": ["GB", "WO"],
            "territories": ["GB"],
            "basicSearch": None,  # 动态替换
            "fTMStatus": ["Filed", "Registered"],
            "fields": [
                "ST13",
                "markImageURI",
                "tmName",
                "tmOffice",
                "applicationNumber",
                "applicationDate",
                "tradeMarkStatus",
                "niceClass",
                "applicantName",
            ],
        },
        "DE": {
            "page": "1",
            "pageSize": "30",
            "criteria": "I",
            "offices": ["DE", "EM", "WO"],
            "territories": ["DE"],
            "basicSearch": None,  # 动态替换
            "fTMStatus": ["Filed", "Registered"],
            "fields": [
                "ST13",
                "markImageURI",
                "tmName",
                "tmOffice",
                "applicationNumber",
                "applicationDate",
                "tradeMarkStatus",
                "niceClass",
                "applicantName",
            ],
        },
    }

    def __init__(self, region=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db = AmazonBrand()
        self.region = region.upper()  # 统一转为大写（如 UK, DE）
        self.brand_all = db.get_brands_by_region(region=self.region)

        # 获取对应国家的模板（如果不存在则抛出异常）
        self.json_data_template = self.COUNTRY_JSON_TEMPLATES.get(self.region)
        if self.json_data_template is None:
            raise ValueError(f"Unsupported region: {self.region}")

        self.headers = {
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,ko;q=0.6,ar;q=0.5',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json; charset=utf-8',
            'Origin': 'https://www.tmdn.org',
            'Referer': 'https://www.tmdn.org/tmview/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }

    def start_requests(self):
        for brand in self.brand_all:
            # 复制模板并替换 brand
            json_data = self.json_data_template.copy()
            json_data["basicSearch"] = brand

            yield scrapy.Request(
                url=self.start_urls[0],
                method="POST",
                body=json.dumps(json_data),
                meta={'brand': brand, 'region': self.region},  # 传递 region
                headers=self.headers,
                callback=self.parse
            )

    def parse(self, response, **kwargs):
        brand = response.meta['brand']
        region = response.meta['region']  # 从 meta 获取 region
        item = ProductItem()
        result = json.loads(response.text)

        item['brand'] = brand
        item['region'] = region  # 使用动态 region
        item['status'] = 1 if result['totalResults'] > 0 else 0
        yield item
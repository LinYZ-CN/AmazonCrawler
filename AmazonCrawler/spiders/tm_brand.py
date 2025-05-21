import json

import scrapy

from AmazonCrawler.items import ProductItem
from AmazonCrawler.sql.amazon_brand import AmazonBrand


class TmBrandSpider(scrapy.Spider):
    name = "tm_brand"
    allowed_domains = ["www.tmdn.org"]
    start_urls = ["https://www.tmdn.org/tmview/api/search/results"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db = AmazonBrand()
        self.brand_all = db.get_brands_by_region(region="UK")

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
            json_data = {
                'page': '1',
                'pageSize': '30',
                'criteria': 'I',
                'offices': [
                    'GB',
                    'WO',
                ],
                'territories': [
                    'GB',
                ],
                'basicSearch': brand,
                'fTMStatus': [
                    'Filed',
                    'Registered',
                ],
                'fields': [
                    'ST13',
                    'markImageURI',
                    'tmName',
                    'tmOffice',
                    'applicationNumber',
                    'applicationDate',
                    'tradeMarkStatus',
                    'niceClass',
                    'applicantName',
                ],
            }
            yield scrapy.Request(
                url=self.start_urls[0],
                method="POST",
                body=json.dumps(json_data),
                meta={'brand': brand},
                headers=self.headers,
                callback=self.parse
            )


    def parse(self, response, **kwargs):
        brand = response.meta['brand']
        item = ProductItem()
        result = json.loads(response.text)
        if result['totalResults'] == 0:
            item['brand'] = brand
            item['region'] = 'UK'
            item['status'] = 0
            yield item
        else:
            item['brand'] = brand
            item['region'] = 'UK'
            item['status'] = 1
            yield item


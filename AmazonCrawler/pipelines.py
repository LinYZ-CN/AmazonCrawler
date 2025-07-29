# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from parsel.xpathfuncs import regex

from AmazonCrawler.sql.amazon_brand import AmazonBrand
from AmazonCrawler.sql.amazon_product import AmazonProduct
from AmazonCrawler.sql.seller_crawler import AmazonSellerCrawlerDB
from AmazonCrawler.sql.uspto_brand import UsptoBrand


class AmazonSellerCrawlerPipeline:
    def __init__(self):
        self.db_crawl = AmazonSellerCrawlerDB()
    def process_item(self, item, spider):
        if spider.name == "seller_asin":
            seller_id = item['seller_id']
            asin = item['asin']
            region = item['region']
            self.db_crawl.mark_as_crawled(seller_id=seller_id, region=region, success=True)
            self.db_crawl.insert_seller_product(seller_id=seller_id, asin=asin,delivery='', region=region)

        elif spider.name == "seller_shop":
            asin = item['asin']
            seller_id = item['seller_id']
            region = item['region']
            delivery = item['delivery']
            self.db_crawl.mark_as_crawled(asin=asin, region=region, success=True)
            self.db_crawl.insert_seller_product(seller_id=seller_id, asin=asin,delivery=delivery, region=region)

        elif spider.name in ["product_info","best_seller"]:
            db_product = AmazonProduct()
            asin = item['asin']
            brand = item['brand']
            price = item['price']
            sale = item['sale']
            region = item['region']
            db_product.insert_product(asin=asin, brand=brand, price=price, sale=sale, region=region)
        elif spider.name in ["jpo_brand", "tm_brand"]:
            db_brand = AmazonBrand()
            brand = item['brand']
            region = item['region']
            status = item['status']
            db_brand.update_brand_status(brand=brand, region=region, status=status)

        elif spider.name in ["uspto_brand"]:
            uspto_brand = UsptoBrand()
            item = {
                "serial_number": item['serial_number'],
                "registration_number": item['registration_number'],
                "transaction_date": item['transaction_date'],
                "filing_date": item['filing_date'],
                "registration_date": item['registration_date'],
                "status_code": item['status_code'],
                "status_date": item['status_date'],  # 更晚
                "mark_identification": item['mark_identification'],
                "attorney_name":item['attorney_name'],
                "case_file_owner_name": item['case_file_owner_name'],
            }
            uspto_brand.insert_or_update_brand(item)
        return item
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


class AmazonSellerCrawlerPipeline:
    def __init__(self):
        self.db_crawl = AmazonSellerCrawlerDB()
        self.db_product = AmazonProduct()
        self.db_brand = AmazonBrand()
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
            asin = item['asin']
            brand = item['brand']
            price = item['price']
            sale = item['sale']
            region = item['region']
            self.db_product.insert_product(asin=asin, brand=brand, price=price, sale=sale, region=region)
        elif spider.name in ["jpo_brand", "tm_brand"]:
            brand = item['brand']
            region = item['region']
            status = item['status']
            self.db_brand.update_brand_status(brand=brand, region=region, status=status)
        return item
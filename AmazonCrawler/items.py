# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class AmazoncrawlerItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class ProductItem(scrapy.Item):
    asin = scrapy.Field()
    brand = scrapy.Field()
    price = scrapy.Field()
    sale = scrapy.Field()
    status = scrapy.Field()
    region = scrapy.Field()


class AsinSellerItem(scrapy.Item):
    asin = scrapy.Field()
    seller_id = scrapy.Field()
    delivery = scrapy.Field()
    region = scrapy.Field()


class SellerAsinItem(scrapy.Item):
    seller_id = scrapy.Field()
    asin = scrapy.Field()
    region = scrapy.Field()



class UsptoItem(scrapy.Item):
   serial_number = scrapy.Field()
   registration_number = scrapy.Field()
   transaction_date = scrapy.Field()
   filing_date = scrapy.Field()
   registration_date = scrapy.Field()
   status_code = scrapy.Field()
   status_date = scrapy.Field()
   mark_identification = scrapy.Field()
   attorney_name = scrapy.Field()
   case_file_owner_name = scrapy.Field()
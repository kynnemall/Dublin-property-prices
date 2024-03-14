# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class PropertyScraperItem(Item):
    url = Field()
    price = Field()
    ber = Field()
    address = Field()
    postcode = Field()
    property_type = Field()
    bedrooms = Field()
    bathrooms = Field()

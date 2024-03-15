import os
import re
import scrapy
import pandas as pd
from datetime import datetime
from dagshub.upload import Repo
from ..items import PropertyScraperItem


class DublinSpider(scrapy.Spider):
    name = 'dublin'
    allowed_domains = ['www.property.ie']
    start_urls = ['https://www.property.ie/property-for-sale/dublin/']

    def parse(self, response):
        urls = response.css('h2 a::attr(href)').extract()
        prices = response.css('h3::text').extract()
        addresses = response.css('h2 a::text').extract()
        bers = response.css('.ber-search-results img').extract()
        summaries = response.css('h4::text').extract()

        for url, price, address, ber, summary in zip(urls, prices, addresses,
                                                     bers, summaries):
            item = PropertyScraperItem()
            item['url'] = url

            # format price and BER
            price = ''.join([i for i in price if i.isdigit()])
            item['price'] = int(price) if price else 0

            if ber:
                item['ber'] = re.search(r'ber_(.*?)\.', ber).group(1)
            else:
                item['ber'] = ''

            # format address
            address = (address
                       .replace(', Ireland', '')
                       .replace(', Co. Dublin', '')
                       .replace('\\', '')
                       .replace('\n', '')
                       .strip())

            # process summary info and extract beds, baths, postcode, and
            # property type e.g. apartment, house, etc.
            summary = summary.replace('\n', '').strip()

            num_beds = re.search(r'(\d+) Bed', summary)
            num_beds = num_beds.group(1) if num_beds else ''
            num_baths = re.search(r'(\d+) Bath', summary)
            num_baths = num_baths.group(1) if num_baths else ''
            property_type = summary.split(',')[-1].strip()
            postcode = re.findall(r'Dublin (\d+)', address)
            if postcode:
                postcode = 'D' + postcode[0].zfill(2)
            else:
                postcode = address.split(', ')[-1]

            # add summary items to item object
            item['address'] = address
            item['postcode'] = postcode
            item['property_type'] = property_type
            item['bedrooms'] = num_beds
            item['bathrooms'] = num_baths
            yield item

        # if another page is available, get more data
        pages = response.css('#pages a').extract()
        contains_next = ['Next' in p for p in pages]
        next_button = any(contains_next)

        if next_button:
            next_url_idx = contains_next.index(True)
            next_url = pages[next_url_idx].split('"')[1]
            yield response.follow(next_url, self.parse)

    # below from https://stackoverflow.com/questions/54656702/scrapy-spider-close
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(
            spider.spider_closed, signal=scrapy.signals.spider_closed
        )
        return spider

    def spider_closed(self, spider):
        """
        When the spider has scraped all the data, prepare the dataset for 
        uploading to Dagshub. Crosscheck with most recent dataset to avoid
        uploading the same data again.

        Parameters
        ----------
        spider : scrapy spider
            The spider scraping the data

        Returns
        -------
        None.

        """

        # process the dataframe before upload
        df = pd.read_csv('data/data.csv')
        today = f"{datetime.now().date()}"
        savename = f"data/{today}_properties.csv"

        # remove 1e6 => price > 0, beds == 0, and bathrooms == NaN
        df = df[(df["bedrooms"] > 0) & (df["price"] > 0) & (df["price"] <= 1e6)
                & (~df["bathrooms"].isna())]
        df["url"] = df["url"].str.split("for-sale/").str[1]
        df.drop(columns=["address"], inplace=True)
        df.to_csv(savename, index=False)
        os.remove("data/data.csv")

        # back up the new data to Dagshub
        with open("token.txt", "r") as f:
            token = f.read().replace('\n', '')
        repo = Repo("kynnemall", "Dublin-property-prices", token=token)
        repo.upload(local_path=savename, remote_path=savename,
                    commit_message=f"Dataset acquired on {today}",
                    versioning="dvc")

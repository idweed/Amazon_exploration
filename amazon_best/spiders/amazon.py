import scrapy


class AmazonSpider(scrapy.Spider):
    name = 'amazon'
    allowed_domains = ['amazon.fr']
    handle_httpstatus_list = [404, 503]
    RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 404, 403, 429]
    download_delay = 1
    CONCURRENT_REQUESTS = 32
    CONCURRENT_REQUESTS_PER_DOMAIN = 32
    AUTOTHROTTLE_ENABLED = False
    crawlera_enabled = True
    crawlera_apikey = 'f19b424ab0d745af938b8f9f3af948f8'
    # start_urls = ['https://www.amazon.fr/gp/bestsellers/appliances/13519571031/ref=zg_bs_pg_2?ie=UTF8&pg=1', 'https://www.amazon.fr/gp/bestsellers/appliances/13519571031/ref=zg_bs_pg_2?ie=UTF8&pg=2']
    
    def start_requests(self):
        # Shuffle pages to try to avoid bans
        for page in [1,2]:
            #url = f'https://www.amazon.fr/gp/bestsellers/appliances/13519571031/ref=zg_bs_pg_2?ie=UTF8&pg={page}'
            url = 'https://www.amazon.fr/gp/bestsellers/music/ref=zg_bs_pg_2?ie=UTF8&pg='+str(page)
            yield scrapy.Request(url)

    def parse(self, response):
        for book in response.xpath('//div[@class="a-column a-span12 a-text-center _cDEzb_grid-column_2hIsc"]'):
            item = {
                'rank': book.xpath('.//span[@class="zg-bdg-text"]/text()').extract_first(),
                'title': book.xpath('.//div[@class="_cDEzb_p13n-sc-css-line-clamp-3_g3dy1"]/text()').extract_first(),
                'price': book.xpath(u'.//span[@class="p13n-sc-price"]/text()').extract_first(),
                'asin': book.xpath(u'.//div[@class="p13n-sc-uncoverable-faceout"]/@id').extract_first(),
                'link' : book.xpath(u'.//a[@role="link"]/@href').extract_first(),
                'img_preview':book.xpath(u'.//img/@src').extract_first(),
                #response.xpath(u'normalize-space(//span[contains(@class,"offer-price")])').extract_first()
            }
            yield scrapy.http.request.Request(
                'https://www.amazon.fr/dp/'+item['asin'],
                callback=self.parse_detailed_offer,
                meta={u"item": item})

    def parse_detailed_offer(self, response):
        item = response.meta[u"item"]
        availability = response.xpath(u'normalize-space(//div[@id="availability"]/span)').extract_first()
        if availability == u'Voir les offres de ces vendeurs.':  # edge case when no availability clearly displayed but product is available
            item[u"availability"] = u"En stock."
        elif availability:
            item[u"availability"] = availability
        yield item
        
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
            url = 'https://www.amazon.fr/gp/bestsellers/dvd/ref=zg_bs_pg_2?ie=UTF8&pg='+str(page)
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
                'https://www.amazon.fr'+item['link'],
                callback=self.parse_detailed_offer,
                meta={u"item": item})

    def search_publication_date(self, s):
        """
        :param s:
        :return:
        """
        rs = re.search(self.publication_date_re, s)
        if rs:
            return rs.group()

    def scrape_brand(self, item, response):
        """
        :param item:
        :param response:
        :return:
        """
        brand = response.xpath(u'normalize-space(//a[@id="brand"]/text())').extract_first()
        if brand:
            item[u'brand'] = brand
        else:
            item[u'brand'] = response.xpath(u'//td[@class="value"]/text()').extract_first()

    def scrape_title(self, item, response):
        """
        :param item:
        :param response:
        :return:
        """
        title = response.xpath(u'normalize-space(//span[@id="productTitle"])').extract_first()
        if title:
            item[u"title"] = title

    def scrape_availability(self, item, response):
        """
        :param item:
        :param response:
        :return:
        """
        availability = response.xpath(u'normalize-space(//div[@id="availability"]/span)').extract_first()
        if availability == u'Voir les offres de ces vendeurs.':  # edge case when no availability clearly displayed but product is available
            item[u"availability"] = u"En stock."
        elif availability:
            item[u"availability"] = availability

    def scrape_description(self, item, response):
        """
        :param item:
        :param response:
        :return:
        """
        description = response.xpath(
            u'//div[@id="productDescription"]/p[not(preceding-sibling::h3) or preceding-sibling::h3[1][.!="Critique"]]').extract_first()
        if description is not None:
            item[u"description"] = description

    def scrape_lowest_price(self, item, response):
        """
        :param item:
        :param response:
        :return:
        """
        offer_price = response.xpath(u'normalize-space(//span[contains(@id,"priceblock_ourprice")])').extract_first()
        if not offer_price:
            offer_price = response.xpath(u'normalize-space(//span[@id="priceblock_saleprice"])').extract_first()
            is_new_offer = u"neuf" in response.xpath(
                u'normalize-space(//span[@class="olp-padding-right"]/a)').extract_first()
            if not offer_price and is_new_offer:  # if no clear price, only in format '[x] neuf a partir de EUR [y]'
                offer_price = response.xpath(
                    u'normalize-space(//span[@class="olp-padding-right"]/span[@class="a-color-price"])').extract_first()
        if offer_price:
            item[u"offer_price"] = offer_price.replace(u"EUR ", u"")

    def parse_offer_listing(self, response):
        """
        :param response:
        :return:
        """
        try:  # This page is either not the first one or the first one
            item = response.meta[u"item"]
        except KeyError:
            item = items.PricingItem()
            item[u"sku"] = str(response.meta[u"sku"])
        offers_selector_list = response.xpath(u'//div[@class="a-row a-spacing-mini olpOffer"]')
        if not offers_selector_list:  # Dismiss if no offer was found
            self.logger.info(u"Failed to find any offer for sku: " + item[u"sku"])
            return

        for offer_selector in offers_selector_list:
            if offer_selector.xpath(
                    u'normalize-space(div[@class="a-column a-span3 olpConditionColumn"]/div[@class="a-section a-spacing-small"]/span[@class="a-size-medium olpCondition a-text-bold"])').extract_first() != u"Neuf":
                continue  # Dismiss the offer if the product is not marked as new
            if offer_selector.xpath(
                    u'div[@class="a-column a-span2 olpSellerColumn"]/h3[@class="a-spacing-none olpSellerName"]/img[@alt="Amazon.fr"]'):
                item[u"stored_price"] = item[u"offer_price"]  # because offer_price loaded is the Amazon price
                continue
            elif offer_selector.xpath(
                    u'div[@class="a-column a-span2 olpSellerColumn"]/h3[@class="a-spacing-none olpSellerName"]/span[@class="a-size-medium a-text-bold"]/a'):
                is_marketplace = True
            else:
                self.logger.error(u"Technical: No seller name found")
                return

            is_lowest_price_yet = False
            is_lowest_price_too = False

            offer_price = offer_selector.xpath(
                u'normalize-space(div[@class="a-column a-span2 olpPriceColumn"]/span[@class="a-size-large a-color-price olpOfferPrice a-text-bold"])').extract_first()
            if not offer_price:
                self.logger.error(u"Technical: No price found")
                continue

            offer_price = u"".join(offer_price.replace(u"EUR ", u"").split(u"."))
            if is_marketplace:
                try:
                    item[u"marketplace_price"]
                except KeyError:
                    item[u"marketplace_price"] = offer_price
                    is_lowest_price_yet = True
                else:
                    if float(offer_price.replace(u",", u".")) < float(item[u"marketplace_price"].replace(u",", u".")):
                        item[u"marketplace_price"] = offer_price
                        is_lowest_price_yet = True
                    elif offer_price == item[u"marketplace_price"]:
                        is_lowest_price_too = True
            else:
                try:
                    item[u"stored_price"]
                except KeyError:
                    item[u"stored_price"] = offer_price
                    is_lowest_price_yet = True
                else:
                    if float(offer_price.replace(u",", u".")) < float(item[u"stored_price"].replace(u",", u".")):
                        item[u"stored_price"] = offer_price
                        is_lowest_price_yet = True
                    elif offer_price == item[u"stored_price"]:
                        is_lowest_price_too = True

        # Go to the next page if there is one, otherwise yield the item if actual data was found
        next_page_url_path = response.xpath(
            u'//div[@class="a-text-center a-spacing-large"]/ul[@class="a-pagination"]/li[@class="a-last"]/a[text() = "Suivant"]/@href').extract_first()
        if next_page_url_path is None:
            # Dismiss the item if no offer price was found
            try:
                item[u"stored_price"]
            except KeyError:
                try:
                    item[u"marketplace_price"]
                except KeyError:
                    self.logger.error(u"Failed to find any offer price")
                    yield item
                    return
            else:
                yield item
        else:
            yield scrapy.http.request.Request(
                self.get_absolute_url(next_page_url_path),
                callback=self.parse_offer_listing,
                meta={u"item": item})

    def scrape_is_stored_or_marketplace(self, item, response):
        """
        :param item:
        :param response:
        :return:
        """
        # stored_offer = response.xpath(u'normalize-space(//span[contains(@id,"priceblock_ourprice")])').extract_first()
        marketplace_offer = response.xpath(u'normalize-space(//span[@id="priceblock_saleprice"])').extract_first()
        stored_offer = response.xpath(
            u'//div[@id="shipsFromSoldBy_feature_div"]/div[@id="merchant-info"]').extract_first()
        if (not stored_offer or u"vendu par Amazon" not in stored_offer):
            item[u"stored_or_marketplace"] = u"marketplace"
        else:
            # if 'neufs', it means that there are marketplace sellers too
            marketplace_offers_too = u"neufs" in response.xpath(
                u'normalize-space(//span[@class="olp-padding-right"]/a)').extract_first()
            if marketplace_offers_too:
                item[u"stored_or_marketplace"] = u"stored_and_marketplace"
            else:
                if not marketplace_offer:
                    item[u"stored_or_marketplace"] = u"stored"

    def scrape_offer_price(self, item, response):
        """
        :param item:
        :param response:
        :return:
        """
        # Scrape the offer price
        offer_price = response.xpath(u'normalize-space(//span[contains(@class,"offer-price")])').extract_first()
        if not offer_price:
            offer_price = response.xpath(
                u'normalize-space(//span[contains(@id,"priceblock_ourprice")])').extract_first()
        if offer_price:
            item[u"offer_price"] = offer_price.replace(u"EUR ", u"")

    def scrape_publication_date(self, item, response):
        publication_date = response.xpath(
            u'normalize-space(//div[@id="detail_bullets_id"]/table/tr/td[@class="bucket"]/div[@class="content"]/ul/li[contains(b,"CD") or contains(b,"Album vinyle")])').extract_first()
        if publication_date:
            publication_date = self.search_publication_date(publication_date)
            if publication_date is not None:
                item[u"publication_date"] = publication_date

            # override

    def parse_detailed_offer(self, response):
        item = response.meta[u"item"]
        # self.logger.debug(item, response)

        item["title"] = response.xpath(u'normalize-space(//span[@id="productTitle"])').extract_first()

        item["publication_date"] = response.xpath(
            u'normalize-space(//div[@id="detail_bullets_id"]/table/tr/td[@class="bucket"]/div[@class="content"]/ul/li[contains(b,"CD") or contains(b,"Album vinyle")])').extract_first()
        item["description"] = response.xpath(
            u'//div[@id="productDescription"]/p[not(preceding-sibling::h3) or preceding-sibling::h3[1][.!="Critique"]]').extract_first()
        self.scrape_availability(item, response)
        #self.scrape_offer_price(item, response)


        yield item
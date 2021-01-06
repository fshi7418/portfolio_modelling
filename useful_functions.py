# -*- coding: utf-8 -*-
"""
Created on Mon Dec 21 18:23:26 2020

@author: Frank Shi
"""
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import holidays
from requests import get
import pandas as pd
import time
import lxml
from lxml import html
from pandas.tseries.offsets import DateOffset


#%
def vlookup(table, item, column_from, column_to):
    '''
    Parameters
    ----------
    table: DataFrame
        a dataframe that has all the information

    item: variant
        item to be looked up, can be string, number, etc.

    column_from: str
        column name where item lives

    column_to: str
        column where the looked up value is

    Returns
    -------
    variant, can be string, number, etc.

    '''
    item_row = table[table[column_from] == item]
    if len(item_row) == 0:
        message = 'no match found when looking for {0} in column {1} from column {2}'
        message = message.format(item, column_to, column_from)
        print(message)
        return None

    if len(item_row) > 1:
        print('multiple matches found, returning first one')

    item_row = item_row.reset_index(drop=True)
    return item_row.loc[0, column_to]


def last_business_day(start_date, country='NA'):
    '''
    Purpose
    -------
    return the latest date before start_date that is a trading day in country

    Parameters
    ----------
    start_date : datetime or date object
        the starting point from which we get the trading day

    country : str, optional
        the country concerned. this has impact on holidays. the default is 'NA',
        which includes canada and usa. other examples include 'USD' or 'CAD'

    Returns
    -------
    datetime object

    '''
    relevant_years = [start_date.year - 1, start_date.year]
    if country == 'NA':
        relevant_holidays = holidays.CA(years=relevant_years) + holidays.US(years=relevant_years)
    elif country == 'CAD':
        relevant_holidays = holidays.CA(years=relevant_years)
    elif country == 'USD':
        relevant_holidays = holidays.US(years=relevant_years)
    date_inc = start_date
    while (date_inc in relevant_holidays) or (date_inc.weekday() >= 5):
        date_inc = date_inc - timedelta(days=1)
    return date_inc


def subdomain_last_price(symbol):
     subdoma = "/quote/{0}"
     subdomain = subdoma.format(symbol)
     return subdomain


def scrape_last_price(url, header):
     page = get(url, headers=header)
     element_html = html.fromstring(page.content)
     elements = element_html.xpath('//*[@id="quote-header-info"]/div[3]/div[1]/div/span[1]')
     return elements


def get_last_price(symbol):
    '''
    Purpose
    -------
    get latest price of a security from the marketwatch website

    Parameters
    ----------
    symbol: str
        security name as displayed in yahoo finance, e.g. ZSP.TO, DLR-U.TO

    Returns
    -------
    datetime object and a floating point value representing price

    '''
    base_url = 'https://finance.yahoo.com'
    url = base_url + subdomain_last_price(symbol)
    url_header = header_function(subdomain_last_price(symbol))
    elements = scrape_last_price(url, url_header)
    price = elements[0].text_content()
    last_price = float(price)
    return datetime.now(), last_price


def get_last_price_old(symbol, instrument, currency):
    '''
    Purpose
    -------
    get latest price of a security from the marketwatch website

    Parameters
    ----------
    symbol: str
        security name, without exchange code, e.g. ZSP

    instrument: str
        'stock' or 'etf', used in web url

    currency: str
        either 'cad' or 'usd', decides url

    Returns
    -------
    datetime object and a floating point value representing price

    '''
    if instrument == 'Stock':
        quote_url_root = 'https://www.marketwatch.com/investing/stock/'
    else:
        quote_url_root = 'https://www.marketwatch.com/investing/fund/'

    url = quote_url_root + symbol
    if currency == 'CAD':
        url = url + '?countrycode=ca'

    quote_site = get(url)
    # print(url)
    quote_soup = BeautifulSoup(quote_site.text, 'html.parser')
    quote = quote_soup.find_all('h3', attrs={'class': 'intraday__price'})[0]
    last_price = quote.find_all('span', attrs={'class': 'value'})

    # us quotes have after hours values and have a different tag
    if len(last_price) == 0:
        last_price = quote.find_all('bg-quote', attrs={'class': 'value'})

    last_price = last_price[0].text
    last_price = float(last_price)

    return datetime.now(), last_price


def format_date(date_datetime):
     date_timetuple = date_datetime.timetuple()
     date_mktime = time.mktime(date_timetuple)
     date_str = str(int(date_mktime))
     return date_str


def subdomain(symbol, start, end, filter='history'):
     subdoma = "/quote/{0}/history?period1={1}&period2={2}&interval=1d&filter={3}&frequency=1d"
     subdomain = subdoma.format(symbol, start, end, filter)
     return subdomain


def header_function(subdomain):
     hdrs =  {"authority": "finance.yahoo.com",
               "method": "GET",
               "path": subdomain,
               "scheme": "https",
               "accept": "text/html",
               "accept-encoding": "gzip, deflate, br",
               "accept-language": "en-US,en;q=0.9",
               "cache-control": "no-cache",
               "dnt": "1",
               "pragma": "no-cache",
               "sec-fetch-mode": "navigate",
               "sec-fetch-site": "same-origin",
               "sec-fetch-user": "?1",
               "upgrade-insecure-requests": "1",
               "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64)"}
     return hdrs


def scrape_page(url, header):
     page = get(url, headers=header)
     element_html = html.fromstring(page.content)
     table = element_html.xpath('//table')
     table_tree = lxml.etree.tostring(table[0], method='xml')
     panda = pd.read_html(table_tree)
     return panda


def split_multiplier(symbol, date):
    '''
    Purpose
    -------
    get the mutliplier that gives the closing price of a security from yahoo finance,
    NOT adjusted for splits

    Parameters
    ----------
    symbol: str
        security name, e.g. ZSP.TO

    date: python datetime
        the date of the price. price is obtained at close

    Returns
    -------
    a multiplier that, if applied to the split-adjusted price, will give the unadjusted price on
    the given date

    '''

    # get the splits

    range_end = datetime(datetime.now().year, datetime.now().month, datetime.now().day)

    start_string = format_date(date)
    end_string = format_date(range_end)

    sub = subdomain(symbol, start_string, end_string, filter='split')
    html_header = header_function(sub)

    base_url = 'https://finance.yahoo.com'
    url = base_url + sub

    split_history = scrape_page(url, html_header)[0]

    # print(split_history)

    multiplier = 1

    for i in split_history.index:
        i_str = split_history.loc[i, 'Open']
        if ':' in i_str:
            ratio_str = i_str.split(' ')[0]
            i_multiplier = int(ratio_str.split(':')[0]) / int(ratio_str.split(':')[1])
            multiplier = multiplier * i_multiplier

    return multiplier


def get_hist_price_wrapper(symbol, date, split_adjust=False):
    '''
    Purpose
    -------
    get closing price of a security from yahoo finance

    Parameters
    ----------
    symbol: str
        security name, e.g. ZSP.TO

    date: python datetime
        the date of the price. price is obtained at close

    split_adjust : bool, optional
        whether to return split-adjusted closing price, default false for
        historical portfolio valuations purposes

    Returns
    -------
    a floating point value representing price

    '''
    # override for DLR-U.TO due to corruption of YFinance data
    if symbol == 'DLR-U.TO':
        return 10.09

    if '.TO' in symbol:
        date = last_business_day(date, country='CAD').date()
    else:
        date = last_business_day(date, country='USD').date()

    print('looking up {} on {}'.format(symbol, date.strftime('%Y-%m-%d')))

    range_end = date + timedelta(days=1)

    start_string = format_date(date)
    end_string = format_date(range_end)

    sub = subdomain(symbol, start_string, end_string)
    html_header = header_function(sub)

    base_url = 'https://finance.yahoo.com'
    url = base_url + sub

    price_history = scrape_page(url, html_header)[0]

    search_string = date.strftime('%b %d, %Y')
    # print('search string is {}'.format(search_string))
    price_str = price_history.loc[price_history['Date'] == search_string, 'Close*']

    if len(price_str) > 1:
        # then there is probably a dividend column somewhere
        choice_col = price_str.apply(lambda x: not any(c.isalpha() for c in x))
        price_str = price_str[choice_col]

    if len(price_str) > 1:
        # if there are still multiple records for the same day, just get the first row
        price_str = price_str.reset_index(drop=True).loc[0, ]

    split_adjusted_close = float(price_str)

    if not split_adjust:
        unadjusted_multiplier = split_multiplier(symbol, date)
        return split_adjusted_close * unadjusted_multiplier

    return split_adjusted_close


def get_hist_price(symbol, date, split_adjust=False):
    try:
        return get_hist_price_wrapper(symbol, date, split_adjust=split_adjust)
    except TypeError:
        print('looking up {} on {} failed, going back a day...'.format(symbol, date.strftime('%Y-%m-%d')))
        date = date - timedelta(days=1)
        return get_hist_price(symbol, date, split_adjust=split_adjust)


def get_hist_fx(pair, date):
    '''
    Purpose
    -------
    get closing exchange of a pair of currencies from yahoo finance

    Parameters
    ----------
    pair: str
        currency pair name, e.g. 'USDCAD' or 'usdcad'

    date: python datetime
        the date of the price. price is obtained at close

    Returns
    -------
    a floating point value representing exchange rate

    '''
    date = last_business_day(date).date()

    range_end = date + timedelta(days=1)

    start_string = format_date(date)
    end_string = format_date(range_end)

    pair = pair.upper()
    if pair[:3] == 'USD':
        symbol = pair[3:] + '%3DX' # url equivalent of '=X'
    else:
        symbol = pair + '%3DX'

    sub = subdomain(symbol, start_string, end_string)
    html_header = header_function(sub)

    base_url = 'https://finance.yahoo.com'
    url = base_url + sub

    price_history = scrape_page(url, html_header)[0]

    # search_string = date.strftime('%b %d, %Y')
    price_str = price_history.loc[0, 'Close*']

    return float(price_str)


def get_last_fx(pair):
    '''
    Purpose
    -------
    get latest fx rates of every pair in fx_pair_list

    Parameters
    ----------
    pair: str
        an fx pair, e.g. 'usdcad'

    Returns
    -------
    float, representing the latest exchange rate

    '''
    fx_url = 'https://www.marketwatch.com/investing/currency/' + pair
    quote_site = get(fx_url)
    # print(url)
    quote_soup = BeautifulSoup(quote_site.text, 'html.parser')
    quote = quote_soup.find_all('h3', attrs={'class': 'intraday__price'})[0]
    last_price = quote.find_all('span', attrs={'class': 'value'})

    # us quotes have after hours values and have a different tag
    if len(last_price) == 0:
        last_price = quote.find_all('bg-quote', attrs={'class': 'value'})

    last_price = last_price[0].text
    last_price = float(last_price)

    return last_price


def get_fx(fx_pair_list, date=None):
    '''
    Purpose
    -------
    get latest fx rates of every pair in fx_pair_list

    Parameters
    ----------
    fx_pair_list: list
        a list of fx pairs, e.g. ['usdcad', 'gbpusd']

    date: datetime
        fx on the closing time of a particular day for getting historical records
        if date is None, then the function will return the latest fx rates

    Returns
    -------
    a dictionary object that uses fx pairs as keys and rates as values

    '''
    fx_dict = {}
    if date is not None:
        for pair in fx_pair_list:
            fx_dict[pair] = get_hist_fx(pair, date)
    else:
        for pair in fx_pair_list:
            fx_dict[pair] = get_last_fx(pair)
    return fx_dict


def past_dates_dict(current_date, inception_date):
    '''
    Purpose
    -------
    construct a correct dictionary of datetime objects based on the inputs

    Parameters
    ----------
    current_date : datetime
        the date right now
    inception_date : datetime
        the date that is the inception date of a portfolio

    Returns
    -------
    a dictionary where keys are return periods (e.g. 'Since Inception', '10 Year', etc.) and values
    are corresponding dates based on current_date

    '''
    answer_dict = {'Since Inception': inception_date}

    if datetime(current_date.year, 1, 1) >= inception_date:
        answer_dict['YTD'] = datetime(current_date.year, 1, 1)

    if current_date - DateOffset(weeks=1) <= inception_date:
        return answer_dict
    else:
        answer_dict['1 Week'] = (current_date - DateOffset(weeks=1)).to_pydatetime()

    months_offset = [1, 3, 6]
    for m in months_offset:
        m_date = (current_date - DateOffset(months=m)).to_pydatetime()
        if m_date <= inception_date:
            return answer_dict
        else:
            answer_dict['{} Month'.format(m)] = m_date

    years_offset = [1, 2, 5, 10]
    for y in years_offset:
        y_date = (current_date - DateOffset(years=y)).to_pydatetime()
        if y_date <= inception_date:
            return answer_dict
        else:
            answer_dict['{} Year'.format(y)] = y_date

    return answer_dict


#% test
if __name__ == '__main__':

    sym = 'CHNA-B.TO'

    d = datetime(2020, 7, 8)

    p = get_hist_price(sym, d)

    print(p)

    m = split_multiplier(sym, d)

    print(m)
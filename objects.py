# -*- coding: utf-8 -*-
"""
Created on Sun Dec 13 18:47:36 2020

@author: Frank Shi
"""
import numpy as np
import pandas as pd
import useful_functions
from datetime import datetime, timedelta
from useful_functions import vlookup, get_last_price, get_fx


def description_to_option(description, currency):
    '''
    Purpose
    -------
    get option information from security description

    Parameters
    ----------
    description: str
        option description from questrade, e.g. 'PUT SPY 04/17/20 224 STANDARD & POORS DEPOSITORY WE ACTED AS AGENT'

    currency: str
        'USD' or 'CAD', adds '.TO' after the underlying symbol if 'CAD'

    Returns
    -------
    Option object

    '''
    description_split = description.split(' ')

    option_type = description_split[0].title()
    spot_symbol = description_split[1].replace('.', '')
    if (currency == 'CAD') and ('.TO' not in spot_symbol):
        spot_symbol = spot_symbol + '.TO'
    expiration = datetime.strptime(description_split[2], '%m/%d/%y')
    strike = float(description_split[3])
    option_symbol = spot_symbol + expiration.strftime('%d%b%Y') + option_type[0] + '{:.2f}'.format(strike)
    return Option(option_symbol, currency, option_type, spot_symbol, expiration, strike)


def questrade_transaction_to_sec(transaction_df):
    '''
    Parameters
    ----------
    transaction_df : DataFrame
        the dataframe exported by questrade

    Returns
    -------
    two dictionaries

    '''

    l = len(transaction_df)
    holdings_dict = {'CAD': 0, 'USD': 0}
    security_dict = {}
    for i in range(l):
        if (i % 50) == 0:
            print('processing row {}'.format(i))
        i_row = transaction_df.loc[i, ]
        i_transaction_date = i_row['Transaction Date']
        i_action = i_row['Action']
        i_symbol = i_row['Symbol']
        i_description = i_row['Description']
        i_quantity = i_row['Quantity']
        i_price = i_row['Price']
        i_gross_amount = i_row['Gross Amount']
        i_commission = i_row['Commission']
        i_net_amount = i_row['Net Amount']
        i_currency = i_row['Currency']
        i_activity = i_row['Activity Type']

        # different cases
        # cash deposit
        if i_activity == 'Deposits':
            holdings_dict[i_currency.upper()] += i_net_amount

        # dividends operate the same way as deposits
        elif i_activity == 'Dividends':
            holdings_dict[i_currency.upper()] += i_net_amount

        # fx conversion is like two deposits at once
        elif i_activity == 'FX conversion':
            holdings_dict[i_currency.upper()] += i_net_amount

        # the opposite of deposits
        elif i_activity == 'Withdrawals':
            holdings_dict[i_currency.upper()] += i_net_amount

        # buying or selling securities
        elif i_activity == 'Trades':
            # first see if it is an option
            i_description_split = i_description.split(' ')
            if (i_description_split[0] == 'PUT') or (i_description_split[0] == 'CALL'): # option
                i_option = description_to_option(i_description, i_currency)
                i_option_symbol = i_option.symbol
                if i_option_symbol not in security_dict.keys():
                    security_dict[i_option_symbol] = i_option

                i_option = security_dict[i_option_symbol]
                i_option.new_trade(i_quantity, i_price * 100, abs(i_commission))

                if i_option.liquidated:
                    del security_dict[i_option_symbol]
                else:
                    security_dict[i_option_symbol] = i_option
            else: # not an option
                if i_symbol not in security_dict.keys():
                    i_security = Security(i_symbol, i_currency)
                    security_dict[i_symbol] = i_security

                i_security = security_dict[i_symbol]
                i_security.new_trade(i_quantity, i_price, abs(i_commission))

                if i_security.liquidated:
                    del security_dict[i_symbol]
                else:
                    security_dict[i_symbol] = i_security

            holdings_dict[i_currency.upper()] += i_net_amount

        # cash or in-knd transfer to and from another investment account
        elif i_activity == 'Transfers':
            if i_action == 'TF6': # transfer in
                if (i_symbol != '') and (not pd.isna(i_symbol)): # in-kind transfer of shares
                    if (i_currency == 'CAD') and ('.TO' not in i_symbol):
                        i_symbol = i_symbol + '.TO'
                    i_price = useful_functions.get_hist_price(i_symbol, i_transaction_date)
                    if i_symbol not in security_dict.keys():
                        i_security = Security(i_symbol, i_currency)
                        security_dict[i_symbol] = i_security
                    i_security = security_dict[i_symbol]
                    i_security.new_trade(i_quantity, i_price, 0) # no commission for in-kind transfer
                else: # cash transfer
                    holdings_dict[i_currency.upper()] += i_net_amount
            elif i_action == 'TFO': # trasnfer out
                if (i_symbol != '') and (not pd.isna(i_symbol)): # transferring securities
                    if (i_currency == 'CAD') and ('.TO' not in i_symbol):
                        i_symbol = i_symbol + '.TO'
                    if i_symbol not in security_dict.keys():
                        print('transferring out non-existent security')
                        return
                    i_security = security_dict[i_symbol]
                    i_security.new_trade(i_quantity, i_price, abs(i_commission))

                    if i_security.liquidated:
                        del security_dict[i_symbol]
                    else:
                        security_dict[i_symbol] = i_security
                else: # transferring out cash
                    holdings_dict[i_currency.upper()] += i_net_amount

        # other activities
        elif i_activity == 'Other':
            if i_action == 'EXP': # option expiry
                i_option = description_to_option(i_description, i_currency)
                i_option_symbol = i_option.symbol
                del security_dict[i_option_symbol]
            elif i_action == 'GST': # tax on fees
                holdings_dict[i_currency.upper()] += i_net_amount
            elif i_action == 'BRW': # journalling
                pass
            elif i_action == 'ADJ': # option adjustment because of splits
                pass

        # fees and rebates
        elif i_activity == 'Fees and rebates':
            if i_action == 'FCH': # fees
                holdings_dict[i_currency.upper()] += i_net_amount
            else:
                pass

        # corporate actions, e.g. splits, name changes
        elif i_activity == 'Corporate actions':
            if i_action == 'CIL': # cash in lieu
                holdings_dict[i_currency.upper()] += i_net_amount
            elif i_action == 'REV': # reverse split
                pass
            elif i_action == 'NAC': # name change
                pass


        # any activities not encountered before
        else:
            print('a new activity not encountered before, exiting...')
            return

    return security_dict, holdings_dict


def investorline_transaction_to_sec(transaction_df):
    '''
    Parameters
    ----------
    transaction_df : DataFrame
        the dataframe exported by bmo investorline

    Returns
    -------
    two dictionaries

    '''

    pass


class TransactionHistory():
    df = pd.DataFrame()
    first_transaction_date = None
    last_transaction_date = None
    current_datetime = None
    broker = ''


    def __init__(self, raw_df_, broker_):
        if broker_ == 'questrade':
            raw_df_['Transaction Date'] = pd.to_datetime(raw_df_['Transaction Date'], format='%Y-%m-%d %H:%M:%S %p')
            raw_df_['Settlement Date'] = pd.to_datetime(raw_df_['Settlement Date'], format='%Y-%m-%d %H:%M:%S %p')
            raw_df_ = raw_df_.sort_values(by='Transaction Date', axis=0).reset_index(drop=True)
            self.df = raw_df_
            self.first_transaction_date = raw_df_['Transaction Date'].min()
            self.last_transaction_date = raw_df_['Transaction Date'].max()
        elif broker_ == 'investorline':
            pass
        self.current_datetime = datetime.today()
        self.broker = broker_


    def print_info(self):
        print('first transaction: {}'.format(self.first_transaction_date.strftime('%Y-%m-%d')))
        print('last transaction: {}'.format(self.last_transaction_date.strftime('%Y-%m-%d')))
        print('asof: {}'.format(self.current_datetime.strftime('%Y-%m-%d')))
        print('broker: ' + self.broker)


class Portfolio():
    current_time = None
    current_holdings = None
    inception_time = None
    external_cash_flow_df = None
    return_dates_dict = {}
    broker = ''
    account_number = None
    account_name = ''

    hist_holdings = {}
    performance = {}
    performance_df = None


    def __init__(self, *args, **kwargs):

        self.current_time = datetime.now()

        # first get the inception date from transaction history

        if kwargs.get('transaction') is not None:

            transaction = kwargs.get('transaction')
            self.current_holdings = Holdings(transaction=transaction)

            if transaction.broker == 'questrade':

                # construct self.external_cash_flow_df
                transaction_df = transaction.df
                cash_flows_df = transaction_df[transaction_df['Activity Type'].isin(['Deposits', 'Withdrawals', 'Transfers'])]

                cash_flows_df['Transaction Date'] = pd.to_datetime(cash_flows_df['Transaction Date'], format='%Y-%m-%d %H:%M:%S %p')
                cash_flows_df['Settlement Date'] = pd.to_datetime(cash_flows_df['Settlement Date'], format='%Y-%m-%d %H:%M:%S %p')
                cash_flows_df = cash_flows_df.sort_values(by='Transaction Date', axis=0).reset_index(drop=True)

                # deal with in-kind transfers based on price at the time of trasfer
                inkind_rows = cash_flows_df[~cash_flows_df['Symbol'].isna()].index
                if len(inkind_rows) > 0:
                    for i in inkind_rows:
                        lookup_symbol = cash_flows_df.loc[i, 'Symbol']
                        if cash_flows_df.loc[i, 'Currency'] == 'CAD':
                            lookup_symbol = lookup_symbol + '.TO'
                        i_price = useful_functions.get_hist_price(lookup_symbol, cash_flows_df.loc[i, 'Transaction Date'])
                        cash_flows_df.loc[i, 'Net Amount'] = i_price * cash_flows_df.loc[i, 'Quantity']

                self.inception_time = cash_flows_df['Transaction Date'].min().to_pydatetime()
                self.external_cash_flow_df = cash_flows_df
                self.account_number = cash_flows_df['Account #'].max()
                self.account_name = cash_flows_df['Account Type'].max()

            elif transaction.broker == 'investorline':
                # input parameters according to bmo dataframe
                # need change column names so that they are consistent with questrade df
                pass

            self.broker = transaction.broker

        if kwargs.get('return_dates_dict') is not None:
            self.return_dates_dict = kwargs.get('return_dates_dict')
        else:
            self.return_dates_dict = useful_functions.past_dates_dict(self.current_time, self.inception_time)

        if kwargs.get('info_df') is not None:
            self.current_holdings.market_value_cad(kwargs.get('info_df'))

        self.hist_holdings = {}
        self.performance = {}
        self.performance_df = None


    def get_hist_holdings(self, transaction, info_df):
        if self.broker == 'questrade':
            for rd in self.return_dates_dict.keys():
                print(rd, ': from {}'.format(self.return_dates_dict[rd].strftime('%Y-%m-%d')))
                self.hist_holdings[rd] = Holdings(transaction=transaction, asof_date=self.return_dates_dict[rd])
                self.hist_holdings[rd].market_value_cad(info_df, hist_date=self.return_dates_dict[rd])
        elif self.broker == 'investorline':
            for rd in self.return_dates_dict.keys():
                print(rd)
                self.hist_holdings[rd] = Holdings(investorline_transaction=transaction, asof_date=self.return_dates_dict[rd])
                self.hist_holdings[rd].market_value_cad(info_df, hist_dates=self.return_dates_dict[rd])


    def measure_performance(self):
        ending_balance = self.current_holdings.market_value
        ending_time = self.current_time
        for rd in self.return_dates_dict:
            starting_balance = self.hist_holdings[rd].market_value
            starting_time = self.return_dates_dict[rd]
            rd_cash_flows = self.external_cash_flow_df.set_index('Transaction Date')
            rd_cash_flows = rd_cash_flows[(rd_cash_flows.index > starting_time) & (rd_cash_flows.index <= ending_time)]
            cash_flow_sum = rd_cash_flows['Net Amount'].sum()

            # construct weighted sum
            rd_cash_flows['Time Weight'] = (ending_time - rd_cash_flows.index) / (ending_time - starting_time)
            weighted_sum = rd_cash_flows['Time Weight'].dot(rd_cash_flows['Net Amount'])

            # compute the rate of return based on the modified Dietz method
            numerator = ending_balance - starting_balance - cash_flow_sum
            denominator = starting_balance + weighted_sum
            self.performance[rd] = numerator / denominator
        self.performance_df = pd.DataFrame(self.performance, index=[self.current_time.strftime('%Y-%m-%d %H:%M')])


    def print_current_holdings(self):
        print('Current: {}'.format(self.current_time.strftime('%Y-%m-%d %H:%M:%S')))
        self.current_holdings.print_info()


    def print_hist_holdings(self):
        for hh in self.hist_holdings.keys():
            print(hh + ':' + ' ' + self.return_dates_dict[hh].strftime('%Y-%m-%d %H:%M:%S'))
            self.hist_holdings[hh].print_info()


    def output_file(self, filename):
        with pd.ExcelWriter(filename, mode='w') as writer:
            self.current_holdings.to_df().to_excel(writer, sheet_name='Current Holdings', index=False)
            self.performance_df.to_excel(writer, sheet_name='Performance Asof')


class Holdings():
    symbol_list = []
    security_list = []
    cash_dict = {}
    fx_pairs = ['usdcad']
    fx_dict = {}
    market_value = 0
    asof_time = None


    def __init__(self, *args, **kwargs):

        if kwargs.get('transaction') is not None:

            transaction = kwargs.get('transaction')
            transaction_df = transaction.df

            if transaction.broker == 'questrade':
                if kwargs.get('asof_date') is not None:
                    transaction_df = transaction_df[transaction_df['Transaction Date'] <= kwargs.get('asof_date')]
                    self.asof_time = kwargs.get('asof_date')

                print('constructing holdings via transaction history data...')
                sec_dict, cash_dict_ = questrade_transaction_to_sec(transaction_df)
                self.symbol_list = list(sec_dict.keys())
                self.security_list = list(sec_dict.values())
                self.cash_dict = cash_dict_

            elif transaction.broker == 'investorline':
                # execute investorline modelling
                pass


    def update_fx(self, hist_date=None):
        self.fx_dict = get_fx(self.fx_pairs, hist_date)


    def get_security_info(self, info_df, symbol_col='ticker_summary'):
        # fill in region, asset class, instrument, etc.
        l = len(self.security_list)
        for i in range(l):
            self.security_list[i].update_security_info(info_df, symbol_col)


    def get_market_price(self, info_df, symbol_col='ticker_summary', hist_date=None):
        # get market price
        l = len(self.security_list)
        for i in range(l):
            self.security_list[i].update_market_price(info_df, symbol_col, date=hist_date)


    def market_value_cad(self, info_df, hist_date=None):
        self.update_fx(hist_date=hist_date)
        print('fx updated')
        self.get_security_info(info_df)
        print('security info updated')
        self.get_market_price(info_df, hist_date=hist_date)
        print('security market prices updated')
        market_value = 0
        for ccy in self.cash_dict.keys():
            if ccy == 'CAD':
                market_value += self.cash_dict[ccy]
            else:
                market_value += self.cash_dict[ccy] * self.fx_dict['{}cad'.format(ccy.lower())]
        for sec in self.security_list:
            if sec.currency == 'CAD':
                market_value += sec.quantity * sec.market_price
            else:
                market_value += sec.quantity * sec.market_price * self.fx_dict['{}cad'.format(sec.currency.lower())]
        print('conversion to cad completed')
        self.market_value = market_value
        if hist_date is not None:
            self.asof_time = hist_date
        else:
            self.asof_time = datetime.now()


    def print_cash_info(self):
        for k in self.cash_dict.keys():
            print('{}: {:.2f}'.format(k, self.cash_dict[k]))


    def print_info(self):
        self.print_cash_info()
        print('securities:', list(self.symbol_list))
        for sec in self.security_list:
            sec.print_basic_info()
        if self.asof_time is not None:
            print('market value: {:.2f}CAD, at {}'.format(self.market_value, self.asof_time.strftime('%Y-%m-%d %H:%M:%S')))


    def to_df(self, with_cash=True):
        # convert to pandas dataframe
        symbol_list = []
        currency_list = []
        instrument_list = []
        quantity_list = []
        asset_class_list = []
        region_list = []
        market_price_local_ccy_list = []
        market_price_time_list = []
        book_cost_local_ccy_list = []

        option_type_list = []
        underlying_symbol_list = []
        underlying_market_price_list = []
        underlying_market_price_time_list = []
        expiration_list = []
        strike_list = []
        l = len(self.security_list)
        for i in range(l):
            i_sec = self.security_list[i]
            symbol_list.append(i_sec.symbol)
            currency_list.append(i_sec.currency)
            instrument_list.append(i_sec.instrument)
            quantity_list.append(i_sec.quantity)
            asset_class_list.append(i_sec.asset_class)
            region_list.append(i_sec.region)
            market_price_local_ccy_list.append(i_sec.market_price)
            market_price_time_list.append(i_sec.market_price_time)
            book_cost_local_ccy_list.append(i_sec.average_cost)
            if i_sec.instrument == 'Option':
                option_type_list.append(i_sec.option_type)
                underlying_symbol_list.append(i_sec.underlying_symbol)
                underlying_market_price_list.append(i_sec.underlying_market_price)
                underlying_market_price_time_list.append(i_sec.underlying_market_price_time)
                expiration_list.append(i_sec.expiration)
                strike_list.append(i_sec.strike)
            else:
                option_type_list.append('NA')
                underlying_symbol_list.append('')
                underlying_market_price_list.append(np.nan)
                underlying_market_price_time_list.append(np.nan)
                expiration_list.append(np.nan)
                strike_list.append(np.nan)

        if with_cash:
            for cash in self.cash_dict:
                symbol_list.append(cash)
                currency_list.append(cash)
                instrument_list.append('Cash')
                quantity_list.append(self.cash_dict[cash])
                asset_class_list.append('Cash')
                region_list.append('Cash')
                market_price_local_ccy_list.append(1)
                market_price_time_list.append(self.asof_time)
                book_cost_local_ccy_list.append(1)
                option_type_list.append('NA')
                underlying_symbol_list.append(np.nan)
                underlying_market_price_list.append(np.nan)
                underlying_market_price_time_list.append(np.nan)
                expiration_list.append(np.nan)
                strike_list.append(np.nan)

        df = pd.DataFrame({'Symbol': symbol_list, 'Currency': currency_list, 'Instrument': instrument_list,
                           'Quantity': quantity_list, 'Asset Class': asset_class_list, 'Region': region_list,
                           'Market Price': market_price_local_ccy_list, 'Price Time': market_price_time_list,
                           'Book Cost': book_cost_local_ccy_list, 'Option Type': option_type_list,
                           'Option Underlying': underlying_symbol_list, 'Underlying Market Price': underlying_market_price_list,
                           'Underlying Price Time': underlying_market_price_time_list, 'Expiration': expiration_list,
                           'Strike Price': strike_list})

        df['Market Price CAD'] = df['Market Price']
        df.loc[df['Currency'] == 'USD', 'Market Price CAD'] = df['Market Price'] * self.fx_dict['usdcad']

        df['Book Cost CAD'] = df['Book Cost']
        df.loc[df['Currency'] == 'USD', 'Book Cost CAD'] = df['Book Cost'] * self.fx_dict['usdcad']
        df['Market Value CAD'] = df['Quantity'] * df['Market Price CAD']

        df['PnL CAD'] = (df['Market Price CAD'] - df['Book Cost CAD']) * df['Quantity']

        df['Pct Return'] = df['Market Price CAD'] / df['Book Cost CAD'] - 1

        df['Pct Portfolio'] = df['Market Value CAD'] / df['Market Value CAD'].sum()

        return df


class Security():
    symbol = ''
    currency = ''
    instrument = ''
    asset_class = ''
    region = ''
    quantity = 0
    average_cost = 0
    market_price = 0
    market_price_time = None
    commission = 0
    liquidated = False


    def __init__(self, symbol_, currency_, instrument_='', asset_class_='', region_=''):
        self.symbol = symbol_
        self.currency = currency_
        self.instrument = instrument_
        self.asset_class = asset_class_
        self.region = region_


    def new_trade(self, new_quantity, new_price, new_commission):
        new_num_shares = self.quantity + new_quantity
        self.commission += new_commission
        if new_quantity > 0: # buy
            new_average_cost = (self.quantity * self.average_cost + new_quantity * new_price + new_commission) / new_num_shares
            self.average_cost = new_average_cost
        if new_num_shares == 0:
            self.liquidated = True
        self.quantity = new_num_shares


    def update_security_info(self, info_table, symbol_col):
        self.instrument = vlookup(info_table, self.symbol, symbol_col, 'instrument')
        self.asset_class = vlookup(info_table, self.symbol, symbol_col, 'asset_class')
        self.region = vlookup(info_table, self.symbol, symbol_col, 'region')


    def update_market_price(self, info_table, symbol_col, date=None):
        url_symbol = vlookup(info_table, self.symbol, symbol_col, 'ticker_url')
        if date is not None:
            self.market_price = useful_functions.get_hist_price(self.symbol, date)
            self.market_price_time = date
        else:
            price_pair = get_last_price(url_symbol, self.instrument, self.currency)
            self.market_price = price_pair[1]
            self.market_price_time = price_pair[0]


    def print_info(self):
        print('{}, {}, {}, {}, {}'.format(self.symbol, self.currency, self.instrument, self.asset_class, self.region))
        print('quantity: {}, avg cost: {:.2f}'.format(self.quantity, self.average_cost))
        if self.market_price_time is not None:
            print('market price: {:.2f}, obtained at {}'.format(self.market_price, self.market_price_time.strftime('%Y-%m-%d %H:%M:%S')))
        print('total commission: {:.2f}, liquidated: {}'.format(self.commission, self.liquidated))


    def print_basic_info(self):
        print('{}, {}, quantity: {}, avg cost: {:.2f}, market price: {:.2f}'.format(self.symbol,
                                                                                    self.currency,
                                                                                    self.quantity,
                                                                                    self.average_cost,
                                                                                    self.market_price))


class Option(Security):
    instrument = 'Option'
    option_type = '' # 'Call' or 'Put'
    underlying_symbol = ''
    underlying_market_price = 0
    underlying_market_price_time = None # python datetime object
    expiration = None # python datetime object
    strike = 0


    def __init__(self, symbol_, currency_, option_type_, underlying_symbol_, expiration_, strike_):
        self.symbol = symbol_
        self.currency = currency_
        self.option_type = option_type_
        self.underlying_symbol = underlying_symbol_
        self.expiration = expiration_
        self.strike = strike_


    def update_security_info(self, info_table, symbol_col):
        self.asset_class = vlookup(info_table, self.underlying_symbol, symbol_col, 'asset_class')
        self.region = vlookup(info_table, self.underlying_symbol, symbol_col, 'region')


    def update_market_price(self, info_table, symbol_col, date=None):
        url_symbol = vlookup(info_table, self.underlying_symbol, symbol_col, 'ticker_url')
        lookup_instrument = vlookup(info_table, self.underlying_symbol, symbol_col, 'instrument')
        if date is not None:
            self.underlying_market_price = useful_functions.get_hist_price(self.underlying_symbol, date)
            self.underlying_market_price_time = date
        else:
            price_pair = get_last_price(url_symbol, lookup_instrument, self.currency)
            self.underlying_market_price = price_pair[1]
            self.underlying_market_price_time = price_pair[0]
        # the market price of the option is intrinsic value only due to difficulties of getting market value of options
        if self.option_type == 'Call':
            self.market_price = max(0, self.underlying_market_price - self.strike) * 100
        else:
            self.market_price = max(0, self.strike - self.underlying_market_price) * 100
        self.market_price_time = self.underlying_market_price_time


    def print_contract_info(self):
        print('{}, {}, {}, {}, {}, {}'.format(self.symbol, self.option_type, self.currency, self.instrument, self.asset_class, self.region))
        print('quantity: {}, avg cost: {:.2f}'.format(self.quantity, self.average_cost))
        if self.market_price_time is not None:
            print('market_price: {:.2f}, obtained at {}'.format(self.market_price, self.market_price_time.strftime('%Y-%m-%d %H:%M:%S')))
        if self.expiration is not None:
            print('expiry: {}, strike: {:.2f}'.format(self.expiration.strftime('%Y-%m-%d %H:%M:%S'), self.strike))
        else:
            print('expiration date unavailble')
        print('total commission: {:.2f}, liquidated: {}'.format(self.commission, self.liquidated))


    def print_underlying_info(self):
        print('underlying: {}'.format(self.underlying_symbol))
        if self.underlying_market_price_time is not None:
            print('underlying market price: {:.2f}, obtained at {}'.format(self.underlying_market_price, self.underlying_market_price_time.strftime('%Y-%m-%d %H:%M:%S')))


    def print_info(self):
        self.print_contract_info()
        self.print_underlying_info()



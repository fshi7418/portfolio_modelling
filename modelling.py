# -*- coding: utf-8 -*-
"""
Created on Sun Dec 13 18:14:21 2020

@author: Frank Shi
"""

from datetime import datetime
import pandas as pd

from objects import Security, Option
import useful_functions

#%


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



#% test
if __name__ == '__main__':
    print('modelling.py')

    adj_sell_str = 'PUT USO 07/17/20 5 UNITED STATES OIL FUND LP TRANSFER TO 8529800'
    adj_buy_str = 'PUT USO1 07/17/20 5 UNITED STATES OIL FUND LP 1:8 REV SPLIT DEL:12 USO & CIL TRANSFER FROM 8GPVKV3'

    option_sell = description_to_option(adj_sell_str, 'USD')
    option_buy = description_to_option(adj_buy_str, 'USD')

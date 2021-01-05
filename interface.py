# -*- coding: utf-8 -*-
"""
Created on Sun Dec 13 18:14:38 2020

@author: Frank Shi
"""

#%%
import os
home_dir = r'C:\Users\Frank Shi\Documents\FrankS\Banking & Investing\Huichuan Shi\Questrade'
os.chdir(home_dir)
import json
import pandas as pd
from objects import TransactionHistory, Portfolio

config_filename = 'config.json'
with open(config_filename) as f:
    config = json.load(f)
paths_dict = config['paths']
filename_dict = config['filenames']
login_dict = config['login_credentials']
sheetname_dict = config['info_sheetnames']

info_file = pd.read_excel(os.path.join(home_dir, filename_dict['info_table']), sheet_name=None)
info_table = info_file[sheetname_dict['general_info']]
symbol_lookup_table = info_file[sheetname_dict['transfer_symbol_lookup']]
split_reference_table = info_file[sheetname_dict['split_reference']]

tfsa_transaction_hist = pd.read_excel(os.path.join(os.getcwd(), paths_dict['transaction_hist_folder'], filename_dict['tfsa_transactions']))
rrsp_transaction_hist = pd.read_excel(os.path.join(os.getcwd(), paths_dict['transaction_hist_folder'], filename_dict['rrsp_transactions']))
q_margin_transaction_hist = pd.read_excel(os.path.join(os.getcwd(), paths_dict['transaction_hist_folder'], filename_dict['q_margin_transactions']))

tfsa_output_filename = os.path.join(os.getcwd(), filename_dict['tfsa_output'])
rrsp_output_filename = os.path.join(os.getcwd(), filename_dict['rrsp_output'])
q_margin_output_filename = os.path.join(os.getcwd(), filename_dict['q_margin_output'])

#%% main
# questrade tfsa
tfsa_transactions = TransactionHistory(tfsa_transaction_hist, 'questrade')
tfsa_transactions.update_inkind_transfer(symbol_lookup_table)
tfsa_portfolio = Portfolio(transaction=tfsa_transactions, info_df=info_table)

#% performance measurement
tfsa_portfolio.get_hist_holdings(tfsa_transactions, info_table)
tfsa_portfolio.measure_performance()
tfsa_portfolio.output_file(tfsa_output_filename)


#% questrade rrsp
rrsp_transactions = TransactionHistory(rrsp_transaction_hist, 'questrade')
rrsp_transactions.update_inkind_transfer(symbol_lookup_table)
rrsp_portfolio = Portfolio(transaction=rrsp_transactions, info_df=info_table)

#% performance measurement
rrsp_portfolio.get_hist_holdings(rrsp_transactions, info_table)
rrsp_portfolio.measure_performance()
rrsp_portfolio.output_file(rrsp_output_filename)


#%% questrade margin
q_margin_transactions = TransactionHistory(q_margin_transaction_hist, 'questrade', split_reference_=split_reference_table)
q_margin_transactions.update_inkind_transfer(symbol_lookup_table)
q_margin_transactions.update_corporate_actions(symbol_lookup_table)
q_margin_transactions.update_journalling()
q_margin_transactions.update_misc_symbols(symbol_lookup_table)

#%%
q_margin_portfolio = Portfolio(transaction=q_margin_transactions, info_df=info_table)
q_margin_portfolio.current_holdings.print_info()

# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 13:18:46 2020

@author: Frank Shi
"""

#%% Import packages
import json
import pandas as pd
import streamlit as st
import os

# bmoil_path = r'C:\Users\Frank Shi\Documents\FrankS\Banking & Investing\Huichuan Shi\BMOInvestorLine'
# os.chdir(bmoil_path)
home_dir = r'C:\Users\Frank Shi\Documents\FrankS\Banking & Investing\Huichuan Shi\Questrade'
os.chdir(home_dir)

import charting

#%% read files
config_filename = 'config.json'
with open(config_filename) as f:
    config = json.load(f)
paths_dict = config['paths']
filename_dict = config['filenames']

tfsa_stats = pd.read_excel(os.path.join(os.getcwd(), filename_dict['tfsa_output']), sheet_name=None)
tfsa_holdings = tfsa_stats['Current Holdings']
tfsa_perf = tfsa_stats['Performance Asof']

rrsp_stats = pd.read_excel(os.path.join(os.getcwd(), filename_dict['rrsp_output']), sheet_name=None)
rrsp_holdings = rrsp_stats['Current Holdings']
rrsp_perf = rrsp_stats['Performance Asof']

q_margin_stats = pd.read_excel(os.path.join(os.getcwd(), filename_dict['q_margin_output']), sheet_name=None)
q_margin_holdings = q_margin_stats['Current Holdings']
q_margin_perf = q_margin_stats['Performance Asof']


#%% streamlit

# sidebar
account_list = {'Questrade TFSA': tfsa_holdings, 'Questrade RRSP': rrsp_holdings, 'Questrade Margin': q_margin_holdings}
account_selected = st.sidebar.radio('Choose an account:', list(account_list.keys()))

# tfsa page
st.title('{} Holdings Stats'.format(account_selected))
holdings_displayed = account_list[account_selected]

# exposure by different attributes
charting.barchart_groupby(holdings_displayed, 'Currency', 'Pct Portfolio', 'Holdings by Currency')
charting.barchart_groupby(holdings_displayed, 'Instrument', 'Pct Portfolio', 'Holdings by Instrument')
charting.barchart_groupby(holdings_displayed, 'Region', 'Pct Portfolio', 'Holdings by Region')
charting.barchart_groupby(holdings_displayed, 'Asset Class', 'Pct Portfolio', 'Holdings by Asset Class')

# attribute A by attribute B
st.write('Below is charting the market value of attribute A grouped by attribute B.')
st.write('For example, if attribute A is Region, attribute B is Asset Class, then the chart will display percentage of all regions of each asset class:')
charting.a_by_b_bar(holdings_displayed, 'Region', 'Asset Class', 'Market Value CAD')

st.write('Please make your selection:')
attribute_list = ['Currency', 'Instrument', 'Region', 'Asset Class', 'Symbol']
attribute_a = st.selectbox('I would like to see the exposure of:', attribute_list)
attribute_b = st.selectbox('in each:', attribute_list)
charting.a_by_b_bar(holdings_displayed, attribute_a, attribute_b, 'Market Value CAD')

# top 5 holdings
charting.top5_holdings_bar(holdings_displayed, 'Pct Portfolio', 'Symbol', 'Top 5 Holdings')









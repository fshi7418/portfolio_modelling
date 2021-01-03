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

#%% streamlit

# sidebar
account_list = {'Questrade TFSA': tfsa_holdings, 'Questrade RRSP': rrsp_holdings}
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




# #%% Grab all data
# @st.cache
# def loadSP500():
#     sp500 = pd.read_csv("SPX.csv")
#     return sp500


# @st.cache
# def grabAllStocks():
#     files = []
#     for file in os.listdir():
#         if file.endswith(".csv"):
#             files.append(file)

#     tableList = []
#     for file in files:
#         df = pd.read_csv(file, parse_dates=['Date'], index_col=['Date'])
#         df['Ticker'] = file.replace(".csv","")
#         tableList.append(df) #storing as a list

#     stockData = pd.concat(tableList)
#     return stockData

# #%% Grab Data
# sp500DF = loadSP500()
# df = grabAllStocks()
# tickers = list(df['Ticker'].unique())

# #%% Streamlit Web App
# st.title("Stock Analyzer - Marquee Demo")
# stockPick = st.sidebar.multiselect("Pick the stocks to graph",tickers, ["AAPL"])

# #Date picks
# # d0 = st.date_input("Start Date", min(df.index))
# # d1 = st.date_input("End Date", max(df.index))
# filterDF = df[df['Ticker'].isin(stockPick)]

# x = min(filterDF.index.year)
# y = max(filterDF.index.year)

# y0, y1= st.sidebar.slider("Pick the year range for x-axis",x,y,(x,y))
# filterDF = filterDF.loc[str(y0):str(y1)]

# #Seaborn chart
# # fig, ax = plt.subplots() #solved by add this line
# # ax = sns.lineplot(data=filterDF, x=filterDF.index, y="Close", hue='Ticker')
# # st.pyplot(fig)

# #Plotly Express
# st.write("Stocks selected: " + "; ".join(stockPick))
# fig2 = px.line(filterDF, x=filterDF.index, y="Close", color="Ticker")
# st.plotly_chart(fig2)

# st.write(filterDF)

# #%%
# @st.cache
# def grabGDPData():
#     gdp = px.data.gapminder()
#     return gdp

# df = grabGDPData()
# fig = px.bar(df,
#               x='continent',
#               y='gdpPercap',
#               color='continent',
#               animation_frame='year',
#               animation_group='country',
#               range_y=[0, 1000000])
# st.plotly_chart(fig)




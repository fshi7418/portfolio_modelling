# -*- coding: utf-8 -*-
"""
Created on Fri Jan  1 01:17:33 2021

@author: Frank Shi
"""
import streamlit as st

import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.api as sm #Linear regression
import plotly.express as px
import plotly.graph_objects as go
from plotly import subplots
from plotly.offline import plot

def barchart_groupby(holdings_df, by_column, sum_column, title):
    '''
    Purpose
    -------
    chart a bar chart in streamlit using plotly, without breakdown in each bar

    Parameters
    ----------
    holdings_df : DataFrame
        the dataframe that the chart is based on

    by_column : str
        the name of the column displayed on the x-axis

    sum_column : str
        the name of the column displayed on the y-axis

    title : str
        title of the chart

    Returns
    -------
    None.

    Effects
    -------
    outputs a chart in streamlit

    '''
    df = holdings_df.groupby(by_column)[[sum_column]].sum()
    df = df.sort_values(by=[sum_column], ascending=False)
    fig = px.bar(df, x=df.index, y=sum_column, title=title, text=sum_column)
    fig.update_traces(texttemplate='%{text:.2%}')
    st.plotly_chart(fig)

    # # matplotlib as an alternative
    # m_fig = plt.figure()
    # ax = m_fig.add_subplot(111)
    # ax.bar(df.index, df[sum_column])
    # plt.title(title)
    # for x, y in zip(df.index,
    #                 df[sum_column]):
    #     # label = 'C${:.2f}, {:.2f}%'.format(y, z * 100)
    #     label = '{:.2f}%'.format(y * 100)
    #     plt.annotate(label, (x, y), textcoords='offset points',
    #                  xytext=(0, 10), ha='center')
    # st.pyplot(m_fig)

    return fig


def barchart_detailed(holdings_df, by_column, sum_column, hover_column, title):
    '''
    Purpose
    -------
    chart a bar chart in streamlit using plotly, with breakdown in each bar

    Parameters
    ----------
    holdings_df : DataFrame
        the dataframe that the chart is based on

    by_column : str
        the name of the column displayed on the x-axis

    sum_column : str
        the name of the column displayed on the y-axis

    hover_column : str
        the name of the column displayed when hovering over a data point

    title : str
        title of the chart

    Returns
    -------
    plotly.graph_object.Figure

    Effects
    -------
    outputs a chart in streamlit

    '''
    fig = px.bar(holdings_df, x=by_column, y=sum_column, title=title, text=sum_column, hover_name=hover_column)
    fig.update_traces(texttemplate='%{text:.2%}')
    st.plotly_chart(fig)

    return fig


def top5_holdings_bar(holdings_df, sort_column, column_x, title):
    '''
    Purpose
    -------
    plot the top 5 holdings in a bar chart using plotly

    Parameters
    ----------
    holdings_df : DataFrame
        holdings dataframe

    sort_column : str
        the name of the column that sorts holdings_df

    column_x : str
        the name of the column that appears on the x-axis of the bar chart

    title : str
        title of the chart

    Returns
    -------
    plotly.graph_object.Figure

    Effects
    -------
    plots a chart in streamlit

    '''
    df = holdings_df.sort_values(by=[sort_column], ascending=False)
    if len(df) >= 5:
        df = df.head(5)
    fig = px.bar(df, x=column_x, y=sort_column, title=title, text=sort_column)
    fig.update_traces(texttemplate='%{text:.2%}')
    st.plotly_chart(fig)

    return fig


def a_by_b_bar(holdings_df, a_column, by_b_column, measure_column, title=None, testing=False):
    '''
    Purpose
    -------
    plot measure_column of a_column by each by_b_column, effectively return multiple bar charts
    e.g. plot regional (a_column) percentage (measure) by each asset class (by_b_column)

    Parameters
    ----------
    holdings_df : DataFrame
        holdings dataframe

    a_column : str
        name of the column that appear on the x_axis of each bar charts

    by_b_column : str
        name of the column that determines how many bar charts are plotted (the number of unique
        records in by_b_column is the number of bar charts plotted)

    measure_column : str
        name of the column that makes up the y-axis of each bar chart

    title : str, optional
        title of the overall chart, default None

    testing : bool, optional
        only set to True when this script is run as __main__, in which case the chart will be plotted
        locally in a html instead of being fed to streamlit, default False

    Returns
    -------
    plotly subplot objects

    Effects
    -------
    plots several bar charts in streamlit

    '''

    sorted_by_b = holdings_df.groupby(by_b_column)[[measure_column]].sum()
    sorted_by_b = sorted_by_b.sort_values(by=[measure_column], ascending=False)

    b_unique_values = sorted_by_b.index
    l = len(b_unique_values)

    fig = subplots.make_subplots(rows=1, cols=l, subplot_titles=b_unique_values)

    for i in range(l):
        i_chart_df = holdings_df[holdings_df[by_b_column] == b_unique_values[i]]
        i_groupby = i_chart_df.groupby(a_column)[[measure_column]].sum()
        i_groupby['Pct'] = i_groupby[measure_column] / i_groupby[measure_column].sum()
        i_groupby = i_groupby.sort_values(by=['Pct'], ascending=False)

        # the bar chart
        i_trace = go.Bar(x=i_groupby.index,
                         y=i_groupby['Pct'],
                         name=b_unique_values[i],
                         text=i_groupby['Pct'],
                         textposition='outside',
                         texttemplate='%{text:.2%}')

        fig.append_trace(i_trace, 1, i + 1)

    for i in range(1, l+1):
        fig.update_yaxes(range=[0, 1], row=1, col=i)

    fig['layout'].update(title='{} Exposure of each {}'.format(a_column, by_b_column))
    fig.update_layout(showlegend=False)
    if title is not None:
        fig['layout'].update(title=title)

    if testing:
        plot(fig)
    else:
        st.plotly_chart(fig)

    return fig


#% test
if __name__ == '__main__':
    import pandas as pd
    import os
    from plotly.offline import init_notebook_mode
    init_notebook_mode()

    sheets = pd.read_excel(os.path.join(r'C:\Users\Frank Shi\Documents\FrankS\Banking & Investing\Huichuan Shi\Questrade',
                                     'tfsa_output.xlsx'), sheet_name=None)
    hdf = sheets['Current Holdings']

    a_by_b_bar(hdf, 'Region', 'Asset Class', 'Market Value CAD', testing=True)

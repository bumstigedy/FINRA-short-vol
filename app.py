import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
##############################################################
url='https://api.finra.org/data/group/OTCMarket/name/regShoDaily'
headers = {'Accept': 'application/json'}
cols={'reportingFacilityCode':'exchange',
         'totalParQuantity':'tot_vol',
         'shortParQuantity':'short_vol',
         'marketCode':'market',
         'tradeReportDate':'date',
         'securitiesInformationProcessorSymbolIdentifier':'symbol',
         'shortExemptParQuantity':'exempt_vol'         
     } 
##############################################################################
def get_symbol(symbol): # ticker symbol
    """ performs API query to return data for the specified symbol 
        returns a dataframe and the latest day
    """
    data ={
            "compareFilters": [ 
                                {  "compareType": "equal", 
                                    "fieldName": "securitiesInformationProcessorSymbolIdentifier", 
                                    "fieldValue" : "{}".format(symbol)
                                }
                            ]
            }
    r=requests.post(url,headers=headers,json=data)
    response=r.content
    df=pd.read_json(response)
    df.tradeReportDate=pd.to_datetime(df.tradeReportDate)
    df = df.rename(columns = cols)
    df2=df.groupby(['date']).sum()
    df2['12ema']=df2.tot_vol.ewm(span=12, adjust=False).mean()
    df2['26ema']=df2.tot_vol.ewm(span=26, adjust=False).mean()
    df2['PVO']=100*((df2['12ema']-df2['26ema'])/df2['26ema'])
    df2['signal']=df2.PVO.ewm(span=9, adjust=False).mean()
    latest_day=str(df.date.max().date())
    return df2, latest_day
####################################################################################################

def most_shorted(day):
    """ returns list of most shorted companies for an input day
    """
    data2 ={
            "compareFilters": [ 
                                {  "compareType": "equal", 
                                    "fieldName": "tradeReportDate", 
                                    "fieldValue" : "{}".format(day),
                     
                                },
                                {  "compareType": "greater", 
                                   "fieldName": "totalParQuantity", 
                                "fieldValue" : 1000000,
                                }
                              ]
                            ,"limit" : 5000    
            }
    r2=requests.post(url,headers=headers,json=data2)
    response2=r2.content
    df4=pd.read_json(response2)
    #group by date
    df5=df4.groupby(['tradeReportDate','securitiesInformationProcessorSymbolIdentifier']).sum()
    df5['short_pct']=100*df5.shortParQuantity/df5.totalParQuantity
    df5=df5.sort_values(by='short_pct',ascending=False)
    return df5
################################################################################
df,latest_day=get_symbol('AAPL')
df2= most_shorted(latest_day)
df2.reset_index(inplace=True)
choices=df2['securitiesInformationProcessorSymbolIdentifier'].unique().tolist()
choices=sorted(choices)
################################################################################
def build_dropdown(): # return dropdown
    return dcc.Dropdown(
        id='demo-dropdown',
        options=[{'label':name, 'value':name} for name in choices],
        value='AAPL',
        )
###########################
def build_pvo_chart(df):
    """ build the chart with PVO and volume """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
                    go.Scatter(x=df.index, y=df.PVO, name="PVO"),
                    secondary_y=False,
                )
    fig.add_trace(
                    go.Scatter(x=df.index, y=df.signal, name="signal line"),
                    secondary_y=False,
                )
    fig.add_trace(
                    go.Bar(x=df.index, y=df.tot_vol, name="total volume", marker_color='gray'),
                    secondary_y=True,
                )

    fig.update_layout(
        title="Volume and PVO",
        legend_title=" ",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    
        )
    fig.update_yaxes(title_text="%", secondary_y=False)
    fig.update_yaxes(title_text="volume", secondary_y=True)
    return fig
################################
def build_long_short_chart(df):
    """ build the long short volume chart """
    fig2 = go.Figure(data=[
    go.Bar(name='Long', x=df.index, y=df.tot_vol-df.short_vol),
    go.Bar(name='Short', x=df.index, y=df.short_vol)
    ])
    # Change the bar mode
    fig2.update_layout(barmode='stack',
                        title="Long / Short Volume",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                        
                    )
    return fig2
#################
app = dash.Dash('Example', external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
#
fig = build_pvo_chart(df)
#

fig2= build_long_short_chart(df)
#######
#
fig3 = go.Figure(data=
                    [
                    go.Bar(name='Long', x=df2.securitiesInformationProcessorSymbolIdentifier.iloc[0:20], y=df2.short_pct.iloc[0:20])
    
   
                    ]
                    
                )
fig3.update_layout( title="Most Shorted Stocks",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                    
                    )

# Change the bar mode
#########
app.title = 'Short Volume Analysis'
#

#
app.layout = html.Div(
    [
        dbc.Row(dbc.Col(html.Div('Select a ticker',className='app-header'))),
        dbc.Row(dbc.Col(build_dropdown())),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id='PVO-chart',figure=fig)),
                dbc.Col(dcc.Graph(id='long-short-chart',figure=fig2)),
                dbc.Col()
                
            ]),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(figure=fig3)),
                dbc.Col(),
                
            ]
        
        ),
    ]
)

@app.callback(
    Output('PVO-chart', 'figure'),
    Output('long-short-chart', 'figure'),
    Input('demo-dropdown', 'value'))
def update_charts(selected_ticker):
    df,latest_day=get_symbol(selected_ticker)
    fig = build_pvo_chart(df)
    fig2= build_long_short_chart(df)
    return fig, fig2


if __name__ == '__main__':
    app.run_server(debug=True)
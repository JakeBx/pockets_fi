import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

import plotly.graph_objs as go
from plotly import tools

from fs_gcsfs import GCSFS
import pandas as pd
import json

gcsfs = GCSFS(bucket_name="pockets-data")
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


def download_csv_to_df(source_name):
    """Opens csv from google cloud and returns a dataframe"""
    with gcsfs.open(source_name, 'r') as f:
        df = pd.read_csv(f)

    return df


dash_app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
dash_app.title = 'Simple Pockets'

app = dash_app.server
DAYS = 255

options = []

tickers = download_csv_to_df('tickers.csv')
df_po = download_csv_to_df('portfolio.csv')
df_plots = download_csv_to_df('plot_json.csv')

colors = ['rgb(247,251,255)', 'rgb(222,235,247)', 'rgb(198,219,239)', 'rgb(158,202,225)', 'rgb(107,174,214)',
          'rgb(66,146,198)', 'rgb(33,113,181)', 'rgb(8,81,156)', 'rgb(8,48,107)']
colors_keep = ['rgb(247,251,255)', 'rgb(222,235,247)', 'rgb(198,219,239)', 'rgb(158,202,225)', 'rgb(107,174,214)',
               'rgb(66,146,198)', 'rgb(33,113,181)', 'rgb(8,81,156)', 'rgb(8,48,107)']
colors.reverse()
final_colors = colors + colors_keep
n = 17
colourmap = [[float(idx) / n, clr] for idx, clr in enumerate(final_colors)]

colors_pie = colors = ['rgb(141,211,199)', 'rgb(255,255,179)', 'rgb(190,186,218)', 'rgb(251,128,114)',
                       'rgb(128,177,211)', 'rgb(253,180,98)', 'rgb(179,222,105)', 'rgb(252,205,229)',
                       'rgb(217,217,217)']

for tic in tickers.Tickers:
    # {'label': 'user sees', 'value': 'script sees'}
    tic = tic.replace('(', '')
    tic = tic.replace(')', '')
    my_dict = {'label': tic, 'value': tic}
    options.append(my_dict)

dash_app.layout = html.Div([
    html.H1('Pockets Portfolio Dashboard'),
    dcc.Markdown('''This is a quick dashboard we put together for a friend who is using CommBank Pockets.
    If you are interested the code is available on [github](https://github.com/JakeBx/pockets_fi).'''),
    dcc.Markdown(''' --- '''),
    # Relative Price Plot
    html.Div([html.H3('Relative Returns'),
              dcc.Dropdown(
                  id='my_ticker_symbol',
                  options=options,
                  value=df_po.Ticker,
                  multi=True
              ),
              html.Button(id='submit-button',
                          n_clicks=0,
                          children='Submit'
                          )
              ], style={'display': 'inline-block', 'verticalAlign': 'top', 'width': '75%'},
             ),
    dcc.Graph(id='price-graph',
              figure={'data': [{'x': [1, 2], 'y': [3, 1]}],
                      'layout': go.Layout(title='Relative Stock Returns Comparison',
                                     yaxis={'title': 'Returns', 'tickformat': ".2%"})}
              ),

    # Single Price Plot
    dcc.Markdown(''' --- '''),
    html.H3('Indvidual Price Action'),
    dcc.Dropdown(
        id='individual-ticker',
        options=options,
        value=df_po.Ticker[0],
        style={'width': '30%'}
    ),
    dcc.Graph(id='individual-graph',
              figure={'data': [
                  {'x': [1, 2], 'y': [3, 1]}

              ], 'layout': go.Layout(title='Relative Stock Returns Comparison',
                                     height=900
                                     )}
              ),
    dcc.Markdown(''' --- '''),
    # Correlation Plot
    html.Div([
        html.H3('Holdings Correlation'),
        dcc.Graph(id='correlation-graph',
                  figure=json.loads(df_plots[df_plots.Plot == 'Correlation'].JSON.values[0])
                  )
    ]),
    dcc.Markdown(''' --- '''),
    # Efficient Frontier
    html.Div([
        html.Div([
            html.H3('Efficient Frontier'),
            dcc.Graph(id='efficent_frontier',
                      figure=json.loads(df_plots[df_plots.Plot == 'EF'].JSON.values[0])
                      ),
            dcc.Markdown('''While there is not that much going on in between these 7 ETFs the plot uses mean-variance
            optimisation to draw that straight line.'''),
        ], style={'width': '65%', 'display': 'inline-block', 'vertical-align': 'top'}),
        html.Div([
            html.H3('Diversification', style={'margin-top': '20px'}),

            dcc.Graph(id='diversification_bar',
                      figure=json.loads(df_plots[df_plots.Plot == 'DiverseBar'].JSON.values[0])
                      ),
            dcc.Markdown('Given our current Portfolio we can move towards the EF by increasing the allocation of ETHI'),
        ], style={'width': '30%', 'vertical-align': 'top', 'text-align': 'centre',
                  'display': 'inline-block'})
    ])
], style={'margin-left': '2.5%', 'margin-right': '2.5%'})


@dash_app.callback(Output('price-graph', 'figure'),
                   [Input('submit-button', 'n_clicks')],
                   [State('my_ticker_symbol', 'value')])
def update_graph(n_clicks, stock_ticker):
    """Updates the relative returns graph with user selected tickers"""
    traces = []
    for tic in stock_ticker:
        df = download_csv_to_df(f'{tic}.csv')
        traces.append({'x': df.Date, 'y': (df['Close'] / df['Close'].iloc[0]) - 1, 'name': tic})

    fig = {
        'data': traces,
        'layout': {'title': stock_ticker}
    }
    return fig


@dash_app.callback(Output('individual-graph', 'figure'),
                   [Input('individual-ticker', 'value')],
                   [State('my_ticker_symbol', 'value')])
def update_individual(stock_ticker, value):
    """Updates the individual price actions plot with user input field"""
    df = download_csv_to_df(f'{stock_ticker}.csv')
    trace1 = go.Ohlc(x=df.Date,
                     open=df['Open'],
                     high=df['High'],
                     low=df['Low'],
                     close=df['Close'],
                     name='Price')

    trace2 = go.Bar(x=df.Date,
                    y=df.Volume,
                    name='Volume')

    fig = tools.make_subplots(rows=2, cols=1, shared_xaxes=True, row_width=[1, 4])
    fig.append_trace(trace1, 1, 1)
    fig.append_trace(trace2, 2, 1)

    fig.layout.xaxis['rangeslider'] = dict(visible=False)

    return fig


if __name__ == '__main__':
    dash_app.run_server(debug=True)

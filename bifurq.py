#! /usr/bin/python3

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import numpy as np
import pandas

# /!\ change NB_STEP_COEF to have a higher-density line on the bifurq
# plot, or make it smaller to improve the plotting performance

NB_STEP_COEF = 250 # number of X ticks on the bifurq plot

N_COMPUTE = 80 # iterate N times over r*x*(1-x)
KEEP = 15 # keep the last N numbers of the r*x*(1-x) tail
ROUND = 3 # round float to N decimal digits

# initial values of UI controls
INITIAL_VALUE=0.6
START_COEF = 1
END_COEF = 4
FOCUS_COEF=3.56

ZOOMS = {0: (START_COEF, END_COEF, FOCUS_COEF),
         1: (3, 3.8, FOCUS_COEF),
         2: (3.45, 3.8, FOCUS_COEF),
         3: (3.543, 3.58, FOCUS_COEF),
}

external_stylesheets = [# 'https://codepen.io/chriddyp/pen/bWLwgP.css' # served via assets/bWLwgP.css and automatically included
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


app.layout = html.Div([
    html.Div([
        html.Div(className='two columns', children=[
            "Initial value: ", html.Span(id='span-initial-value'), html.Br(),
            dcc.Slider(id='input-initial-value', value=INITIAL_VALUE, step=0.1, min=0, max=1), html.Br(),
            "Start coef ", html.Br(),
            dcc.Input(id='input-start-coef', value=START_COEF, type='number'), html.Br(),
            "End coef ", html.Br(),
            dcc.Input(id='input-end-coef', value=END_COEF, type='number'), html.Br(),
            "Zoom ",
            dcc.Dropdown(id='input-zoom', value=0, options=[{'label':i, 'value': i} for i in ZOOMS], clearable=False, style={"width": "164px"}),
        ]),
        html.Div(className='ten columns', children=[
            dcc.Graph(id='graph-overview')
        ]),
    ]),

    html.Hr(),
    html.Div([
        html.Div(className='two columns', children=[
            html.Hr(),
            "Focus on coefficient ", html.Br(),
            dcc.Input(id='input-focus-coef', value=FOCUS_COEF, type='number', step=0.001),

            dcc.RadioItems(id='input-show-full', value='yes',
                options=[{'label': 'Show the full population evolution', 'value': 'yes'},
                         {'label': 'Show only the tail', 'value': 'no'}]),
            html.Hr(),
        ]),
        html.Div(className='five columns', children=[
            dcc.Graph(id='graph-focus'),
        ]),
        html.Div(className='five columns', children=[
            dcc.Graph(id='graph-distrib'),
        ]),
    ]),
])


def compute_evolution(start, r, full=False):
    x = start
    vals = [x]
    for _ in range(N_COMPUTE):
        x = r*x*(1-x)
        vals.append(x)

    return vals if full else vals[-KEEP:]

@app.callback(
    [Output('input-start-coef', 'value'),
     Output('input-end-coef', 'value'),
     Output('input-focus-coef', 'value')],
    [Input('input-zoom', 'value'), Input('graph-overview', 'clickData')])
def update_coef(zoom, clickData):
    trigger = dash.callback_context.triggered[0]["prop_id"]

    if trigger.startswith('graph-overview'):
        if not clickData: # nothing was clicked (app is loading)
            return dash.no_update, dash.no_update, dash.no_update

        return dash.no_update, dash.no_update, round(clickData['points'][0]['x'], 2)

    # triggered by click on zoom

    try:
        return ZOOMS[zoom]
    except KeyError:
        return START_COEF, END_COEF, FOCUS_COEF

@app.callback(
    Output('graph-focus', 'figure'),
    [Input('input-initial-value', 'value'),
     Input('input-focus-coef', 'value'),
     Input('input-show-full', 'value')])
def draw_focus(init_value, coef, str_full):
    if None in (init_value, coef):
        return dash.no_update

    full = str_full == "yes"
    y = compute_evolution(init_value, coef, full=full)

    x = range(N_COMPUTE) if full else range(N_COMPUTE-KEEP, N_COMPUTE)

    fig = go.Figure(data=go.Scatter(x=list(x), y=y))

    fig.update_layout(title={
        'text': "Population Evolution",
        'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'})

    return fig

@app.callback(
    Output('span-initial-value', 'children'),
    [Input('input-initial-value', 'value')])
def update_initial_value(value):
    return str(value)

@app.callback(
    [Output('graph-overview', 'figure'), Output('graph-distrib', 'figure')],
    [Input('input-initial-value', 'value'), Input('input-focus-coef', 'value'),
     Input('input-start-coef', 'value'), Input('input-end-coef', 'value'),])
def draw_overview(init_value, focus_coef, start_coef, end_coef):
    if None in (init_value, focus_coef, end_coef, start_coef):
        return [dash.no_update, dash.no_update]

    step_coef = (end_coef-start_coef) / NB_STEP_COEF

    print("Start", start_coef, end_coef, start_coef)
    x = []
    overview_y = []
    current_coef = start_coef

    count_x = []
    count_y = []
    first_value = None

    while current_coef <= end_coef:
        vals = compute_evolution(init_value, current_coef)
        if first_value is None: first_value = max(vals)
        count_x.append(current_coef)
        count_y.append(len({round(v, ROUND) for v in vals}))

        for v in vals:
            if v < first_value: continue

            x.append(current_coef)
            overview_y.append(v)

        current_coef += step_coef

    focus_y = [] if not first_value or focus_coef < start_coef or focus_coef > end_coef else \
        [v for v in compute_evolution(init_value, focus_coef) if v > first_value]

    fig_overview = go.Figure(data=[go.Scatter(x=x, y=overview_y, mode="markers"),
                          go.Scatter(x=[focus_coef for _ in focus_y], y=focus_y,
                                     mode="markers", marker=dict(color="red"))])
    fig_overview.update_layout(showlegend=False)
    fig_overview.update_layout(title={
        'text': "Bifurcation Diagram",
        'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'})
    print("Done")

    has_coef = [y for x, y in zip(count_x, count_y) if x <= focus_coef]

    focus_coef_count = has_coef[-1] if has_coef else 0

    fig_count = go.Figure(data=[go.Scatter(x=count_x, y=count_y)])

    fig_count.update_layout(title={
        'text': "Number of solution",
        'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'})

    fig_count.update_layout(
        annotations=[
            go.layout.Annotation(
                x=focus_coef,
                y=focus_coef_count,
                xref="x", yref="y", text=f"coef {focus_coef}: {focus_coef_count} solutions",
                showarrow=True, arrowhead=7,
                ax=-40, ay=-40,
            )
        ]
    )
    return fig_overview, fig_count


if __name__ == '__main__':
    app.run_server(debug=True)

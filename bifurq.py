#! /usr/bin/python3

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import numpy as np
import pandas
import types


# /!\ change NB_STEP_COEF to have a higher-density line on the bifurq
# plot, or make it smaller to improve the plotting performance

NB_STEP_COEF = 250 # number of X ticks on the bifurq plot

N_COMPUTE = 80 # iterate N times over r*x*(1-x)
KEEP = 15 # keep the last N numbers of the r*x*(1-x) tail
ROUND = 3 # round float to N decimal digits

DEFAULTS = types.SimpleNamespace()
# initial values of UI controls
DEFAULTS.INITIAL_VALUE = 0.6
DEFAULTS.START_COEF = 1
DEFAULTS.END_COEF = 4
DEFAULTS.FOCUS_COEF = 3.56
DEFAULTS.SHOW_FULL = "yes"
ZOOM = "---"

ZOOMS = {
    "---": (0, 0, 0),
    0: (DEFAULTS.START_COEF, DEFAULTS.END_COEF, DEFAULTS.FOCUS_COEF),
    1: (3, 3.8, DEFAULTS.FOCUS_COEF),
    2: (3.45, 3.8, DEFAULTS.FOCUS_COEF),
    3: (3.543, 3.58, DEFAULTS.FOCUS_COEF),
}

external_stylesheets = [# 'https://codepen.io/chriddyp/pen/bWLwgP.css' # served via assets/bWLwgP.css and automatically included
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets,
                suppress_callback_exceptions=True,
)

def build_layout(vals=None):
    if not vals: vals = DEFAULTS

    return html.Div([
        html.Div([
            html.Div(className='two columns', children=[
                "Initial value: ", html.Span(id='span-initial-value'), html.Br(),
                dcc.Slider(id='input-initial-value', value=vals.INITIAL_VALUE, step=0.1, min=0, max=1), html.Br(),
                "Start coef ", html.Br(),
                dcc.Input(id='input-start-coef', value=vals.START_COEF, type='number'), html.Br(),
                "End coef ", html.Br(),
                dcc.Input(id='input-end-coef', value=vals.END_COEF, type='number'), html.Br(),
                "Zoom: ",
                dcc.Dropdown(id='input-zoom', value=ZOOM, options=[{'label':i, 'value': i} for i in ZOOMS], clearable=False, style={"width": "164px"}),
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
                dcc.Input(id='input-focus-coef', value=vals.FOCUS_COEF, type='number', step=0.001),

                dcc.RadioItems(id='input-show-full', value=vals.SHOW_FULL,
                    options=[{'label': 'Show the full population evolution', 'value': 'yes'},
                             {'label': 'Show only the tail', 'value': 'no'}]),
                html.Hr(),
                html.Div(id='focus-solutions', children=["..."]),
                html.Hr(),
                html.P(html.A('Permalink', href='', id='permalink'))
            ]),
            html.Div(className='five columns', children=[
                dcc.Graph(id='graph-focus'),
            ]),
            html.Div(className='five columns', children=[
                dcc.Graph(id='graph-distrib'),
            ]),
        ]),
    ])

app.layout = html.Div([html.Div(id='page-content'),
                       dcc.Location('url', refresh=False)])

def compute_evolution(start, r, full=False):
    x = start
    vals = [x]
    for _ in range(N_COMPUTE):
        x = r*x*(1-x)
        vals.append(x)

    return vals if full else vals[-KEEP:]

INPUT_NAMES = [i.lower().replace("_", "-") for i in DEFAULTS.__dict__]
@app.callback(
    Output('permalink', 'href'),
    [Input(f"input-{input_name}", 'value') for input_name in INPUT_NAMES])
def get_permalink(*args):
    return "?"+"&".join(f"{k}={v}" for k, v in zip(INPUT_NAMES, map(str, args)))

@app.callback(Output('page-content', 'children'),
              [Input('url', 'search')])
def display_page(search):
    import urllib.parse
    search_dict = urllib.parse.parse_qs(search[1:]) if search else {}

    def get_val(k):
        try: v = search_dict[k.lower().replace("_", "-")][0]
        except KeyError: return None

        try: return int(v)
        except ValueError: pass

        try: return float(v)
        except ValueError: pass

        return v

    input_dict = {k:get_val(k) for k in DEFAULTS.__dict__ if get_val(k)}
    new_initial_values = types.SimpleNamespace()
    new_initial_values.__dict__.update(DEFAULTS.__dict__) # make sure no value is missing
    new_initial_values.__dict__.update(input_dict)

    return build_layout(new_initial_values)

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

    if zoom == "---":
        return dash.no_update, dash.no_update, dash.no_update

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

@app.callback(
    Output('focus-solutions', 'children'),
    [Input('graph-overview', 'figure')],
    [State('input-focus-coef', 'value')])
def update_solutions(graph, focus_coef):
    if not graph:
        return "Solutions not computed yet."

    solutions = graph['data'][1]['y']
    sol_str = ", ".join(sorted({f"{s:.3f}" for s in solutions}))
    return html.Span([f"Solutions for coef={focus_coef}:", html.Br(), sol_str])

if __name__ == '__main__':
    app.run_server(debug=True)

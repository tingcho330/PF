from dash import dcc, html
import dash_bootstrap_components as dbc

def create_layout(app):
    return html.Div([
        dcc.Graph(id='equipment-graph'),
        html.Div(id='selected-node', style={'display': 'none'}),
        html.Div([
            dcc.Input(id='start-node', type='text', placeholder='Start Node', style={'margin-right': '10px'}),
            dcc.Input(id='end-node', type='text', placeholder='End Node', style={'margin-right': '10px'}),
            html.Button('Find Path', id='find-path', n_clicks=0, style={'margin-right': '10px'}),
            dcc.Dropdown(
                id='filter-dropdown',
                options=[{'label': '특정 노드 포함 필터', 'value': 'node'}],
                placeholder='필터 조건 선택',
                style={'width': '300px', 'margin-right': '10px'}
            ),
            dcc.Input(id='filter-input', type='text', placeholder='필터 값 입력', style={'margin-right': '10px'}),
            html.Button('출력', id='output-button', n_clicks=0, style={'margin-right': '10px'}),
            html.Button('주장비 우선 정렬', id='sort-priority-button', n_clicks=0, style={'margin-right': '10px'}),
            html.Button('단거리 우선 정렬', id='sort-shortest-button', n_clicks=0)
        ], style={'display': 'flex', 'align-items': 'center', 'flex-wrap': 'wrap', 'margin-bottom': '20px'}),
        dcc.Dropdown(id='path-dropdown', options=[], placeholder='Select a path', style={'margin-bottom': '10px', 'width': '100%'}),
        html.Div(id='path-output'),
        html.Div(id='path-count', style={'margin-bottom': '20px'}),
        html.Div(id='controls', children=[]),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("경로 정보")),
                dbc.ModalBody(id='modal-body'),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close", className="ml-auto")
                ),
            ],
            id="modal",
        ),
    ], style={'padding': '20px'})

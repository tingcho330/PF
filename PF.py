import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback_context, ALL
import dash_bootstrap_components as dbc

# 엑셀 파일에서 데이터 읽기
file_path = 'pf_example.xlsx'  # 엑셀 파일 경로를 여기에 입력하세요
df = pd.read_excel(file_path)

# 설비의 초기 상태를 모두 on으로 설정
df['상태'] = 'on'

# 그래프 생성 함수
def create_graph(df):
    G = nx.DiGraph()
    for index, row in df.iterrows():
        level = row['레벨']
        equipment = row['장비 이름']
        parent_equipments = row['부모 장비']
        
        # 노드 추가 시 'level' 속성을 설정
        G.add_node(equipment, level=level, status=row['상태'])
        
        if pd.notna(parent_equipments):
            for parent_equipment in parent_equipments.split(','):
                parent_equipment = parent_equipment.strip()
                G.add_edge(parent_equipment, equipment)
    return G

# "on" 상태의 설비만 포함된 그래프 생성 함수
def create_graph_with_status(df):
    G = nx.DiGraph()
    for index, row in df[df['상태'] == 'on'].iterrows():
        level = row['레벨']
        equipment = row['장비 이름']
        parent_equipments = row['부모 장비']
        
        # 노드 추가 시 'level' 속성을 설정
        G.add_node(equipment, level=level, status=row['상태'])
        
        if pd.notna(parent_equipments):
            for parent_equipment in parent_equipments.split(','):
                parent_equipment = parent_equipment.strip()
                if df[df['장비 이름'] == parent_equipment]['상태'].values[0] == 'on':
                    G.add_edge(parent_equipment, equipment)
    return G

# 레벨 기반 레이아웃 생성 함수
def hierarchy_pos(G, scale=3):
    pos = {}
    levels = {node: G.nodes[node]['level'] for node in G.nodes()}
    nodes_by_level = sorted(levels.items(), key=lambda x: x[1])
    level_counts = {level: 0 for node, level in nodes_by_level}

    for node, level in nodes_by_level:
        pos[node] = (level_counts[level], -level * scale)  # x값을 같은 레벨의 순서대로 부여하고, y값에 배율 적용
        level_counts[level] += 1
        
    return pos

# Dash 애플리케이션 생성
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# 레이아웃 설정
app.layout = html.Div([
    dcc.Graph(id='equipment-graph'),
    html.Div(id='selected-node', style={'display': 'none'}),
    html.Div([
        dcc.Input(id='start-node', type='text', placeholder='Start Node', style={'margin-right': '10px'}),
        dcc.Input(id='end-node', type='text', placeholder='End Node', style={'margin-right': '10px'}),
        html.Button('Find Path', id='find-path', n_clicks=0, style={'margin-right': '10px'}),
        dcc.Dropdown(
            id='filter-dropdown',
            options=[
                {'label': '길이 기준 필터', 'value': 'length'},
                {'label': '특정 노드 포함 필터', 'value': 'node'}
            ],
            placeholder='필터 조건 선택',
            style={'width': '200px', 'margin-right': '10px'}
        ),
        dcc.Input(id='filter-input', type='text', placeholder='필터 값 입력', style={'margin-right': '10px'}),
        html.Button('출력', id='output-button', n_clicks=0)
    ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '20px'}),
    dcc.Dropdown(id='path-dropdown', options=[], placeholder='Select a path', style={'margin-bottom': '10px'}),
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

@app.callback(
    Output('selected-node', 'children'),
    Input('equipment-graph', 'clickData')
)
def display_click_data(clickData):
    if clickData:
        node = clickData['points'][0]['text']
        return node
    return ''

@app.callback(
    [Output('equipment-graph', 'figure'),
     Output('path-output', 'children'),
     Output('path-count', 'children'),
     Output('path-dropdown', 'options'),
     Output('controls', 'children')],
    [Input('find-path', 'n_clicks'),
     Input('path-dropdown', 'value'),
     Input({'type': 'toggle-status', 'index': ALL}, 'n_clicks')],
    [State('start-node', 'value'),
     State('end-node', 'value'),
     State('controls', 'children'),
     State('filter-dropdown', 'value'),
     State('filter-input', 'value')]
)
def update_graph(path_clicks, selected_path_index, toggle_clicks, start_node, end_node, controls, filter_condition, filter_value):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # 상태 변경
    if 'toggle-status' in triggered_id:
        selected_node = eval(triggered_id.split('.')[0])['index']
        current_status = df.loc[df['장비 이름'] == selected_node, '상태'].values[0]
        new_status = 'off' if current_status == 'on' else 'on'
        df.loc[df['장비 이름'] == selected_node, '상태'] = new_status

    G = create_graph(df)
    pos = hierarchy_pos(G, scale=3)

    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    node_text = []
    node_color = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_color.append('blue' if df[df['장비 이름'] == node]['상태'].values[0] == 'on' else 'red')

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            showscale=False,
            color=node_color,
            size=10,
            line_width=2))

    # y축 레벨 값 설정
    levels = sorted(set(-G.nodes[node]['level'] * 3 for node in G.nodes()))  # scale에 맞춰 y축 값 조정
    level_labels = sorted(set(G.nodes[node]['level'] for node in G.nodes()))
    
    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0, l=0, r=0, t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(
                        showgrid=True, 
                        zeroline=False, 
                        tickvals=levels,
                        ticktext=level_labels
                    )
                 ))

    # Controls for toggling status
    controls = []
    nodes_by_level = sorted(G.nodes(data=True), key=lambda x: x[1]['level'])
    table_header = [
        html.Thead(html.Tr([html.Th("레벨", style={'textAlign': 'center'}), 
                            html.Th("장비명", style={'textAlign': 'center'}), 
                            html.Th("장비상태", style={'textAlign': 'center'}), 
                            html.Th("토글 버튼", style={'textAlign': 'center'})]))
    ]
    table_body = []
    for level in sorted(set(data['level'] for node, data in G.nodes(data=True))):
        for node, data in nodes_by_level:
            if data['level'] == level:
                current_status = df.loc[df['장비 이름'] == node, '상태'].values[0]
                status_color = 'red' if current_status == 'on' else 'green'
                table_body.append(html.Tr([
                    html.Td(level, style={'textAlign': 'center'}),
                    html.Td(node, style={'textAlign': 'center'}),
                    html.Td(current_status, style={'color': status_color, 'textAlign': 'center'}),
                    html.Td(html.Button('Toggle Status', id={'type': 'toggle-status', 'index': node}, n_clicks=0), style={'textAlign': 'center'})
                ]))
    controls = dbc.Table(table_header + [html.Tbody(table_body)], bordered=True, striped=True, hover=True, responsive=True)

    # 경로 찾기 및 시각화
    path_output = ''
    path_count = ''
    dropdown_options = []
    path_traces = []
    
    if start_node and end_node:
        try:
            G_with_status = create_graph_with_status(df)
            pos_with_status = pos
            if start_node not in G_with_status.nodes:
                path_output = f'Start node {start_node} not found in the graph.'
            elif end_node not in G_with_status.nodes:
                path_output = f'End node {end_node} not found in the graph.'
            else:
                all_paths = list(nx.all_shortest_paths(G_with_status, source=start_node, target=end_node))
                
                # 필터 조건 적용
                if filter_condition == 'length':
                    try:
                        filter_value = int(filter_value)
                        filtered_paths = [path for path in all_paths if len(path) == filter_value]
                    except ValueError:
                        filtered_paths = all_paths
                elif filter_condition == 'node':
                    filtered_paths = [path for path in all_paths if filter_value in path]
                else:
                    filtered_paths = all_paths
                
                # 경로 길이 기준으로 정렬
                sorted_paths = sorted(filtered_paths, key=lambda path: len(path))

                path_count = html.Div([
                    html.Span(f"검색된 경로는 {len(sorted_paths)}가지 입니다"),
                    html.Br(), html.Br()  # 2줄 간격 추가
                ])
                
                dropdown_options = [{'label': ' -> '.join(path), 'value': str(index)} for index, path in enumerate(sorted_paths)]
                
                if triggered_id == 'find-path':
                    path_output = ' -> '.join(sorted_paths[0])
                elif triggered_id == 'path-dropdown' and selected_path_index is not None:
                    selected_path = sorted_paths[int(selected_path_index)]
                    path_edges = list(zip(selected_path, selected_path[1:]))
                    
                    edge_x = []
                    edge_y = []
                    for edge in path_edges:
                        x0, y0 = pos_with_status[edge[0]]
                        x1, y1 = pos_with_status[edge[1]]
                        edge_x.append(x0)
                        edge_x.append(x1)
                        edge_x.append(None)
                        edge_y.append(y0)
                        edge_y.append(y1)
                        edge_y.append(None)

                    path_trace = go.Scatter(
                        x=edge_x, y=edge_y,
                        line=dict(width=4, color='green'),
                        hoverinfo='none',
                        mode='lines')
                    path_traces.append(path_trace)

                fig.add_traces(path_traces)
        except nx.NetworkXNoPath:
            path_output = 'No path found.'

    return fig, path_output, path_count, dropdown_options, controls

@app.callback(
    Output("modal", "is_open"),
    [Input("output-button", "n_clicks"), Input("close", "n_clicks")],
    [State("modal", "is_open")]
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@app.callback(
    Output("modal-body", "children"),
    Input("output-button", "n_clicks"),
    [State('path-dropdown', 'value'), State('start-node', 'value'), State('end-node', 'value')]
)
def display_selected_path_info(n_clicks, selected_path_index, start_node, end_node):
    if selected_path_index is not None:
        G_with_status = create_graph_with_status(df)
        selected_path = list(nx.all_shortest_paths(G_with_status, source=start_node, target=end_node))[int(selected_path_index)]
        path_info = []
        for node in selected_path:
            level = G_with_status.nodes[node]['level']
            status = df.loc[df['장비 이름'] == node, '상태'].values[0]
            status_color = 'red' if status == 'on' else 'green'
            path_info.append(html.Tr([
                html.Td(level, style={'textAlign': 'center'}),
                html.Td(node, style={'textAlign': 'center'}),
                html.Td(status, style={'color': status_color, 'textAlign': 'center'})
            ]))
        return html.Table([
            html.Thead(html.Tr([html.Th("레벨", style={'textAlign': 'center'}), 
                                html.Th("장비명", style={'textAlign': 'center'}), 
                                html.Th("상태", style={'textAlign': 'center'})])),
            html.Tbody(path_info)
        ])
    return "경로가 선택되지 않았습니다."

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)

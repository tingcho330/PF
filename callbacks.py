from dash import Input, Output, State, callback_context, ALL
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
from utils import read_excel, create_graph_with_status

# 엑셀 파일 경로
excel_path = "pf_example3.xlsx"
df = read_excel(excel_path)

def register_callbacks(app):
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
         Input('sort-priority-button', 'n_clicks'),
         Input('sort-shortest-button', 'n_clicks'),
         Input('path-dropdown', 'value'),
         Input({'type': 'toggle-status', 'index': ALL}, 'n_clicks')],
        [State('start-node', 'value'),
         State('end-node', 'value'),
         State('controls', 'children'),
         State('filter-dropdown', 'value'),
         State('filter-input', 'value')]
    )
    def update_graph(path_clicks, priority_sort_clicks, shortest_sort_clicks, selected_path_index, toggle_clicks, start_node, end_node, controls, filter_condition, filter_value):
        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # 상태 변경
        if 'toggle-status' in triggered_id:
            selected_node = eval(triggered_id.split('.')[0])['index']
            current_status = df.loc[df['장비 이름'] == selected_node, '상태'].values[0]
            new_status = 'off' if current_status == 'on' else 'on'
            df.loc[df['장비 이름'] == selected_node, '상태'] = new_status

        # 그래프 생성
        G = create_graph_with_status(df)

        pos = nx.multipartite_layout(G, subset_key="level")

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

        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=0),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
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
                G_with_status = create_graph_with_status(df[df['상태'] == 'on'])

                if start_node not in G_with_status.nodes:
                    path_output = f'Start node {start_node} not found in the graph.'
                elif end_node not in G_with_status.nodes:
                    path_output = f'End node {end_node} not found in the graph.'
                else:
                    all_paths = list(nx.all_shortest_paths(G_with_status, source=start_node, target=end_node))

                                        # 필터 조건 적용
                    if filter_condition == 'node' and filter_value:
                        filtered_paths = [path for path in all_paths if filter_value in path]
                    else:
                        filtered_paths = all_paths

                    # 정렬 조건 적용
                    if 'sort-priority-button' in triggered_id:
                        sorted_paths = sorted(filtered_paths, key=lambda path: sum(df[df['장비 이름'].isin(path)]['주예비'] == 'A'), reverse=True)
                    elif 'sort-shortest-button' in triggered_id:
                        sorted_paths = sorted(filtered_paths, key=lambda path: len(path))
                    else:
                        sorted_paths = filtered_paths

                    path_count = html.Div([
                        html.Span(f"검색된 경로는 <b>{len(sorted_paths)}가지</b> 입니다"),
                        html.Br(), html.Br()
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
                            x0, y0 = pos[edge[0]]
                            x1, y1 = pos[edge[1]]
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
            G_with_status = create_graph_with_status(df[df['상태'] == 'on'])

            selected_path = list(nx.all_shortest_paths(G_with_status, source=start_node, target=end_node))[int(selected_path_index)]
            path_info = []
            for node in selected_path:
                level = G_with_status.nodes[node]['level']
                status = df.loc[df['장비 이름'] == node, '상태'].values[0]
                status_color = 'red' if status == 'on' else 'green'
                path_info.append(html.Tr([
                    html.Td(level, style={'textAlign': 'center'}),
                    html.Td(node, style={'textAlign': 'center'}),
                    html.Td(status, style={'color': status_color, 'textAlign': 'center'}),  # PF 권고 상태는 경로 값 상태와 동일하게 설정
                    html.Td("off", style={'color': 'green', 'textAlign': 'center'}),  # 현재 상태는 'off'로 설정
                    html.Td(html.Button('조작', id={'type': 'control-button', 'index': node}, n_clicks=0), style={'textAlign': 'center'})
                ]))
            return html.Table([
                html.Thead(html.Tr([html.Th("레벨", style={'textAlign': 'center'}), 
                                    html.Th("장비명", style={'textAlign': 'center'}), 
                                    html.Th("PF 권고 상태", style={'textAlign': 'center'}), 
                                    html.Th("현재 상태", style={'textAlign': 'center'}), 
                                    html.Th("자동제어", style={'textAlign': 'center'})])),
                html.Tbody(path_info)
            ], style={'width': '100%', 'border': '1px solid black', 'textAlign': 'center'})
        return "경로가 선택되지 않았습니다."

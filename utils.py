import pandas as pd
import networkx as nx

def read_excel(excel_path):
    try:
        df = pd.read_excel(excel_path)
        print("엑셀 파일 읽기 성공")
        # 데이터 프레임에 "상태" 열 추가 및 초기값 설정
        if '상태' not in df.columns:
            df['상태'] = 'on'
        return df
    except Exception as e:
        print(f"엑셀 파일 읽기 오류: {e}")
        return pd.DataFrame()

def create_graph_with_status(df):
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
                # 부모 장비가 데이터프레임에 존재하는지 확인
                if not df[df['장비 이름'] == parent_equipment].empty:
                    if df[df['장비 이름'] == parent_equipment]['상태'].values[0] == 'on':
                        G.add_edge(parent_equipment, equipment)
    return G

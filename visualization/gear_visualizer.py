"""
齒輪可視化模組
"""
import plotly.graph_objects as go
import numpy as np

class GearVisualizer:
    def __init__(self):
        """
        初始化齒輪可視化器
        """
        self.fig = None
        
    def create_basic_visualization(self, pinion_vertices, pinion_faces, 
                                 gear_vertices, gear_faces, transform_info):
        """
        創建基本的齒輪可視化
        
        Args:
            pinion_vertices: 小齒輪頂點
            pinion_faces: 小齒輪面
            gear_vertices: 大齒輪頂點
            gear_faces: 大齒輪面
            transform_info: 變換信息
            
        Returns:
            plotly.graph_objects.Figure: 圖形物件
        """
        fig = go.Figure([
            go.Mesh3d(
                x=pinion_vertices[:, 0], y=pinion_vertices[:, 1], z=pinion_vertices[:, 2],
                i=pinion_faces[:, 0], j=pinion_faces[:, 1], k=pinion_faces[:, 2],
                color='#FFD306', 
                opacity=0.5, 
                flatshading=True, 
                lighting=dict(ambient=0.8, diffuse=0.3, specular=0.1), 
                showscale=False, 
                name='小齒輪 (Pinion)'
            ),
            go.Mesh3d(
                x=gear_vertices[:, 0], y=gear_vertices[:, 1], z=gear_vertices[:, 2],
                i=gear_faces[:, 0], j=gear_faces[:, 1], k=gear_faces[:, 2],
                color='#0066CC', 
                opacity=0.5, 
                flatshading=True, 
                lighting=dict(ambient=0.8, diffuse=0.3, specular=0.1), 
                showscale=False, 
                name='大齒輪 (Gear)'
            ),
            # 中心點標記
            go.Scatter3d(
                x=[transform_info['pinion_center'][0]], 
                y=[transform_info['pinion_center'][1]], 
                z=[transform_info['pinion_center'][2]],
                mode='markers+text', 
                marker=dict(size=8, color='red'), 
                text=["Pinion Center"], 
                name="小齒輪中心"
            ),
            go.Scatter3d(
                x=[transform_info['gear_center'][0]], 
                y=[transform_info['gear_center'][1]], 
                z=[transform_info['gear_center'][2]],
                mode='markers+text', 
                marker=dict(size=8, color='blue'), 
                text=["Gear Center"], 
                name="大齒輪中心"
            ),
            # 中心距離連線
            go.Scatter3d(
                x=[transform_info['pinion_center'][0], transform_info['gear_center'][0]], 
                y=[transform_info['pinion_center'][1], transform_info['gear_center'][1]], 
                z=[transform_info['pinion_center'][2], transform_info['gear_center'][2]],
                mode='lines+markers',
                line=dict(color='black', width=3),
                marker=dict(size=6, color=['red', 'blue']),
                name=f'中心距離 ({transform_info["center_distance"]:.1f}mm)',
                hovertemplate='齒輪中心連線<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title=f'齒輪定位視覺化 (X距離: {transform_info["x_distance"]}mm, Y距離: {transform_info["y_distance"]}mm)',
            scene=dict(
                xaxis_title='X (小齒輪移動軸)', 
                yaxis_title='Y (大齒輪移動軸)', 
                zaxis_title='Z (高度軸)',
                aspectmode='data', 
                camera=dict(eye=dict(x=1, y=1, z=1))
            ),
            margin=dict(t=50,l=0,b=0,r=0),
            showlegend=True
        )
        
        self.fig = fig
        return fig
    
    def add_interference_visualization(self, interference_data):
        """
        添加干涉分析可視化
        
        Args:
            interference_data: 干涉分析資料
        """
        if self.fig is None:
            print("請先建立基本可視化")
            return
        
        # 定義顏色和大小
        marker_colors = {
            'severe_p': 'darkred',   
            'severe_g': 'red',       
            'medium_p': 'orangered', 
            'medium_g': 'orange',    
            'mild_p': 'gold',        
            'mild_g': 'yellow',      
            'contact_p': 'greenyellow', 
            'contact_g': 'lightgreen',  
            'near_p': 'lightblue',   
            'near_g': 'lightskyblue' 
        }
        
        marker_sizes = {
            'severe': 7,      
            'medium': 6,      
            'mild': 5,        
            'contact': 4,     
            'near': 3         
        }
        
        # 添加各等級干涉點
        interference_types = [
            ('severe_p', 'severe', '嚴重干涉-小齒輪'),
            ('severe_g', 'severe', '嚴重干涉-大齒輪'),
            ('medium_p', 'medium', '中度干涉-小齒輪'),
            ('medium_g', 'medium', '中度干涉-大齒輪'),
            ('mild_p', 'mild', '輕微干涉-小齒輪'),
            ('mild_g', 'mild', '輕微干涉-大齒輪'),
            ('contact_p', 'contact', '接觸區-小齒輪'),
            ('contact_g', 'contact', '接觸區-大齒輪'),
            ('near_p', 'near', '接近接觸-小齒輪'),
            ('near_g', 'near', '接近接觸-大齒輪')
        ]
        
        for data_key, size_key, name in interference_types:
            if data_key in interference_data and len(interference_data[data_key]) > 0:
                points = interference_data[data_key]
                self.fig.add_trace(go.Scatter3d(
                    x=points[:, 0], y=points[:, 1], z=points[:, 2],
                    mode='markers',
                    marker=dict(
                        size=marker_sizes[size_key], 
                        color=marker_colors[data_key], 
                        opacity=1.0
                    ),
                    name=f'{name} ({len(points)}點)',
                    hovertemplate=f'{name}<extra></extra>'
                ))
        
        # 更新標題
        self.fig.update_layout(
            title='齒輪干涉與接觸分析'
        )

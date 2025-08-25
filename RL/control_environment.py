import sys
import os
import json
from typing import Tuple, Union
from features.Bevel_gear_vibration_features import compute_feature_values_from_vibration

# 確保專案路徑可被匯入
project_path = os.path.dirname(__file__)
if project_path not in sys.path:
    sys.path.append(project_path)

import numpy as np

try:
    from geometry.gear_loader import GearLoader
    from geometry.gear_transformer import GearTransformer
    from analysis.gear_interference_analyzer import GearInterferenceAnalyzer
    from simulation.gear_vibration_simulator import GearVibrationSimulator
    from analysis.vibration_data_analyzer import VibrationDataAnalyzer
except Exception:
    # 在某些測試或環境下，模組可能不可用；提供輕量替代實作以便測試
    GearLoader = None
    GearTransformer = None
    GearInterferenceAnalyzer = None
    GearVibrationSimulator = None
    VibrationDataAnalyzer = None


def run_analysis_and_get_time_signal_real(x_distance: float, y_distance: float,
                                          offset_deg: float = 10.0,
                                          sample_rate: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """嚴格使用真實模組的版本：不提供模擬退回，回傳 (time, signal)。

    會依序進行：載入 STL → 設定齒輪 → 變換 → 干涉分析(sample_rate) → 振動模擬。
    缺少任何依賴或資料時會拋出例外。
    """
    from geometry.gear_loader import GearLoader  # 強制真實匯入
    from geometry.gear_transformer import GearTransformer
    from analysis.gear_interference_analyzer import GearInterferenceAnalyzer
    from simulation.gear_vibration_simulator import GearVibrationSimulator

    loader = GearLoader()
    transformer = GearTransformer()
    analyzer = GearInterferenceAnalyzer()
    vibration_sim = GearVibrationSimulator()

    pinion_mesh, gear_mesh = loader.load_stl_files()
    if pinion_mesh is None or gear_mesh is None:
        raise RuntimeError("無法載入齒輪模型（請確認 STL 路徑與依賴庫）")

    transformer.setup_gears(pinion_mesh, gear_mesh)
    transformer.reset_gears()

    vp, fp, vg, fg, _ = transformer.transform_gears(
        x_distance=x_distance,
        y_distance=y_distance,
        manual_offset_deg=offset_deg
    )

    analysis = analyzer.analyze_interference(vp, fp, vg, fg, sample_rate=sample_rate)
    vibration_data = vibration_sim.simulate_vibration_signal(analysis)

    if not isinstance(vibration_data, dict):
        raise RuntimeError("振動模擬未回傳 dict，無法抽取時間訊號")

    if 'time' in vibration_data and 'vibration_signal' in vibration_data:
        return vibration_data['time'], vibration_data['vibration_signal']
    raise KeyError("振動資料缺少 'time' 或 'vibration_signal' 鍵")


def run_analysis_and_get_time_signal(x_distance: float, y_distance: float,
                                     offset_deg: float = 10.0,
                                     sample_rate: int = 150) -> dict:
    """執行真實模組流程並回傳『扁平特徵 dict』供 RL 控制器使用。

    注意：此函式回傳的是 Dict[str, float]（非 JSON 字串）。
    Keys 例：
      - Time_rms_x/y/z, Time_crestfactor_x/y/z
      - Powerspectrum_rms_x/y/z, Powerspectrum_skewness_x/y/z, Powerspectrum_kurtosis_x/y/z
    """
    # 取得時間域訊號（真實幾何/分析/模擬流程）
    t, s = run_analysis_and_get_time_signal_real(x_distance, y_distance, offset_deg, sample_rate)

    # 構建 vibration_data dict 給特徵萃取
    assert len(t) == len(s) and len(t) > 0
    fs = None
    if len(t) > 1:
        dt = float(np.mean(np.diff(t)))
        if dt > 0:
            fs = 1.0 / dt

    vibration_data = {
        'time': t,
        'vibration_signal': s,
        'simulation_params': ({'sampling_rate': fs} if fs else {})
    }

    features = compute_feature_values_from_vibration(vibration_data)

    # 萃取並轉成純 float（避免 numpy scalar）
    required_keys = [
        'Time_skewness_x', 'Time_kurtosis_x', 'Time_rms_x', 'Time_crestfactor_x',
        'Powerspectrum_skewness_x', 'Powerspectrum_kurtosis_x', 'Powerspectrum_rms_x', 'Powerspectrum_crestfactor_x',
        'Time_skewness_y', 'Time_kurtosis_y', 'Time_rms_y', 'Time_crestfactor_y',
        'Powerspectrum_skewness_y', 'Powerspectrum_kurtosis_y', 'Powerspectrum_rms_y', 'Powerspectrum_crestfactor_y',
        'Time_skewness_z', 'Time_kurtosis_z', 'Time_rms_z', 'Time_crestfactor_z',
        'Powerspectrum_skewness_z', 'Powerspectrum_kurtosis_z', 'Powerspectrum_rms_z', 'Powerspectrum_crestfactor_z'
    ]

    results: dict[str, float] = {}
    for k in required_keys:
        if k not in features:
            raise KeyError(f"缺少特徵鍵: {k}")
        # 轉成 Python float
        results[k] = float(features[k])

    return results
        


def plot_vibration_time_signal(time: np.ndarray, signal: np.ndarray,
                               title: str | None = None,
                               show: bool = True,
                               save_path: str | None = None) -> bool:
    """繪製振動時間訊號；若安裝了 matplotlib 則顯示/儲存圖表。

    Returns True 如果成功繪圖，否則 False。
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[DEBUG] ⚠️ 無法繪圖：未安裝 matplotlib。可先安裝：pip install matplotlib")
        return False

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time, signal, lw=0.8)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("vib.")
    ax.set_title(title or "Vib. signal")
    ax.grid(True, alpha=0.3)
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[DEBUG] 💾 已儲存圖檔: {save_path}")
    if show:
        plt.show()
    return True


def _gather_interference_points_for_area(analysis: dict) -> np.ndarray:
    """收集用於面積/體積可視化的干涉點（僅 severe/medium/mild）。"""
    ip = analysis.get('interference_points', {})
    groups = []
    for k in ['severe_p', 'severe_g', 'medium_p', 'medium_g', 'mild_p', 'mild_g']:
        pts = ip.get(k)
        if isinstance(pts, np.ndarray) and len(pts) > 0:
            groups.append(pts)
    if groups:
        return np.vstack(groups)
    return np.empty((0, 3))


def build_interference_figure(pinion_vertices: np.ndarray, pinion_faces: np.ndarray,
                              gear_vertices: np.ndarray, gear_faces: np.ndarray,
                              analysis: dict, title: str | None = None):
    """建立含齒輪與干涉面積（凸包）的 3D 視覺化圖形。"""
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("[DEBUG] ⚠️ 無法繪製 3D：未安裝 plotly。可先安裝：pip install plotly")
        return None

    fig = go.Figure()
    # 齒輪 Mesh
    fig.add_trace(go.Mesh3d(
        x=pinion_vertices[:, 0], y=pinion_vertices[:, 1], z=pinion_vertices[:, 2],
        i=pinion_faces[:, 0], j=pinion_faces[:, 1], k=pinion_faces[:, 2],
        color='#FFD306', opacity=0.45, flatshading=True, name='Pinion'
    ))
    fig.add_trace(go.Mesh3d(
        x=gear_vertices[:, 0], y=gear_vertices[:, 1], z=gear_vertices[:, 2],
        i=gear_faces[:, 0], j=gear_faces[:, 1], k=gear_faces[:, 2],
        color='#0066CC', opacity=0.45, flatshading=True, name='Gear'
    ))

    # 干涉點（分類展示）
    try:
        ip = analysis.get('interference_points', {})
        points_layers = [
            ('severe_p', 'darkred', '嚴重-小齒'),
            ('severe_g', 'red', '嚴重-大齒'),
            ('medium_p', 'orangered', '中度-小齒'),
            ('medium_g', 'orange', '中度-大齒'),
            ('mild_p', 'gold', '輕微-小齒'),
            ('mild_g', 'yellow', '輕微-大齒'),
        ]
        for key, color, name in points_layers:
            pts = ip.get(key)
            if isinstance(pts, np.ndarray) and len(pts) > 0:
                fig.add_trace(go.Scatter3d(
                    x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
                    mode='markers', marker=dict(size=3, color=color, opacity=0.9),
                    name=f'{name} ({len(pts)})'
                ))
    except Exception:
        pass

    # 干涉面積：使用凸包建立面網格
    all_pts = _gather_interference_points_for_area(analysis)
    if len(all_pts) >= 4:
        try:
            from scipy.spatial import ConvexHull
            hull = ConvexHull(all_pts)
            simplices = hull.simplices  # (M, 3)
            fig.add_trace(go.Mesh3d(
                x=all_pts[:, 0], y=all_pts[:, 1], z=all_pts[:, 2],
                i=simplices[:, 0], j=simplices[:, 1], k=simplices[:, 2],
                color='crimson', opacity=0.35, name='干涉凸包（面）'
            ))
        except Exception as e:
            print(f"[DEBUG] ⚠️ 無法建立干涉凸包：{e}")

    fig.update_layout(
        title=title or '齒輪干涉區域可視化',
        scene=dict(
            xaxis_title='X', yaxis_title='Y', zaxis_title='Z',
            aspectmode='data', camera=dict(eye=dict(x=1.2, y=1.2, z=1.0))
        ),
        showlegend=True,
        margin=dict(t=50, l=0, b=0, r=0)
    )
    return fig


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Run gear analysis (real modules) and plot time signal')
    parser.add_argument('x', type=float, help='X 距離 (Pinion)')
    parser.add_argument('y', type=float, help='Y 距離 (Gear)')
    parser.add_argument('--offset', type=float, default=10.0, help='旋轉偏移 (度), 預設 10')
    parser.add_argument('--sample', type=int, default=100, help='干涉分析取樣率, 預設 100')
    parser.add_argument('--no-show', action='store_true', help='不顯示圖表（僅儲存）')
    parser.add_argument('--save', type=str, default=None, help='儲存圖檔路徑 (例如 output.png)')
    parser.add_argument('--draw-interf', action='store_true', help='繪製齒輪干涉區域（3D）')
    parser.add_argument('--save-html', type=str, default=None, help='將 3D 視覺化儲存為 HTML')
    args = parser.parse_args()
    run_analysis_and_get_time_signal(args.x, args.y, args.offset, args.sample)
    # try:
    #     t, s = run_analysis_and_get_time_signal_real(args.x, args.y, args.offset, args.sample)
    #     print(f"[DEBUG] time len={len(t)}, signal len={len(s)}")
    #     plot_vibration_time_signal(
    #         t, s,
    #         title=f"Vibration (x={args.x}, y={args.y}, offset={args.offset}°, sample={args.sample})",
    #         show=not args.no_show,
    #         save_path=args.save
    #     )

    #     if args.draw_interf:
    #         # 重新執行幾何與干涉分析以取得幾何與分析資料
    #         from gear_loader import GearLoader
    #         from gear_transformer import GearTransformer
    #         from gear_interference_analyzer import GearInterferenceAnalyzer
    #         loader = GearLoader()
    #         transformer = GearTransformer()
    #         analyzer = GearInterferenceAnalyzer()
    #         pinion_mesh, gear_mesh = loader.load_stl_files()
    #         if pinion_mesh is None or gear_mesh is None:
    #             raise RuntimeError("無法載入齒輪模型，無法繪製干涉區域")
    #         transformer.setup_gears(pinion_mesh, gear_mesh)
    #         transformer.reset_gears()
    #         vp, fp, vg, fg, transform_info = transformer.transform_gears(
    #             x_distance=args.x, y_distance=args.y, manual_offset_deg=args.offset
    #         )
    #         analysis = analyzer.analyze_interference(vp, fp, vg, fg, sample_rate=args.sample)

    #         # 優先使用 GearVisualizer 產生 Plotly 圖並輸出 HTML
    #         fig = None
    #         try:
    #             from gear_visualizer import GearVisualizer
    #             visualizer = GearVisualizer()
    #             fig = visualizer.create_basic_visualization(vp, fp, vg, fg, transform_info)
    #             visualizer.add_interference_visualization(analysis.get('interference_points', {}))
    #             fig = visualizer.fig
    #         except Exception as e:
    #             print(f"[DEBUG] ⚠️ GearVisualizer 產生圖形失敗，改用凸包回退：{e}")
    #             fig = build_interference_figure(
    #                 vp, fp, vg, fg, analysis,
    #                 title=f"干涉區域 (x={args.x}, y={args.y}, offset={args.offset}°, sample={args.sample})"
    #             )

    #         if fig is not None:
    #             if args.save_html:
    #                 try:
    #                     fig.write_html(args.save_html)
    #                     print(f"[DEBUG] 💾 已儲存 3D 視覺化 HTML: {args.save_html}")
    #                 except Exception as e:
    #                     print(f"[DEBUG] ⚠️ 儲存 HTML 失敗：{e}")
    #             if not args.no_show:
    #                 fig.show()
    # except Exception as e:
    #     print(f"[DEBUG] ❌ 執行失敗: {e}")

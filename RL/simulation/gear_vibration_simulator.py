"""
增強版齒輪振動模擬器
修正齒輪頻率重疊問題，增加更多諧波，並移除相位圖
"""


import os
        
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import os
from dotenv import load_dotenv

load_dotenv()
DEBUG=int(os.getenv("DEBUG", 0))


from plotly.subplots import make_subplots
try:
    from config_manager import ConfigManager
except ImportError:
    # 如果config_manager不存在，使用預設值
    ConfigManager = None

class GearVibrationSimulator:
    def __init__(self):
        """
        初始化振動模擬器
        """
        if ConfigManager:
            self.config = ConfigManager()
            vib_params = self.config.get_vibration_params()
            self.fs = vib_params.get('sampling_frequency', 10000)
            self.duration = vib_params.get('signal_duration', 2.0)
        else:
            self.fs = 10000  # 取樣頻率 (Hz)
            self.duration = 2.0  # 信號持續時間 (秒)
            
        self.time = np.linspace(0, self.duration, int(self.fs * self.duration))
        
    def simulate_vibration_signal(self, interference_analysis, rpm_pinion=None, rpm_gear=None):
        """
        基於干涉分析結果模擬振動信號
        
        Args:
            interference_analysis: 干涉分析結果
            rpm_pinion: 小齒輪轉速 (RPM)，從配置文件讀取
            rpm_gear: 大齒輪轉速 (RPM)，從配置文件讀取
            
        Returns:
            dict: 包含振動信號和FFT分析結果
        """
        if(DEBUG):
            print("=== 開始振動信號模擬 ===")
        
        # 從配置文件或使用預設值獲取齒輪參數
        if ConfigManager and self.config:
            gear_params = self.config.get_gear_params()
            if rpm_pinion is None:
                rpm_pinion = gear_params['pinion']['rpm']
            if rpm_gear is None:
                rpm_gear = gear_params['gear']['rpm']
            z_pinion = gear_params['pinion']['teeth']
            z_gear = gear_params['gear']['teeth']
        else:
            # 預設值
            if rpm_pinion is None:
                rpm_pinion = 1800
            if rpm_gear is None:
                rpm_gear = 600  # 修正：使用正確的齒輪比
            z_pinion = 20
            z_gear = 60
            
        gear_ratio = z_gear / z_pinion  # 齒數比
        
        # 基本頻率計算
        f_pinion = rpm_pinion / 60  # 小齒輪頻率 (Hz)
        f_gear = rpm_gear / 60      # 大齒輪頻率 (Hz)
        GMF = f_pinion * z_pinion  # 齒輪嚙合頻率 (Gear Mesh Frequency - GMF) (Hz)
        
        # 驗證齒輪比
        calculated_gear_freq = f_pinion / gear_ratio
        if abs(calculated_gear_freq - f_gear) > 0.1:
            print(f"⚠️ 警告：齒輪頻率不匹配！")
            print(f"   根據齒數比計算的大齒輪頻率: {calculated_gear_freq:.2f} Hz")
            print(f"   設定的大齒輪頻率: {f_gear:.2f} Hz")
            f_gear = calculated_gear_freq  # 使用計算值
        
        # 從干涉分析獲取參數
        severity_score = self._extract_severity_score(interference_analysis)

        if(DEBUG):
            print(f"齒輪參數:")
            print(f"  小齒輪: {z_pinion}齒, {rpm_pinion} RPM ({f_pinion:.2f} Hz)")
            print(f"  大齒輪: {z_gear}齒, {rpm_gear} RPM ({f_gear:.2f} Hz)")
            print(f"  齒數比: {gear_ratio:.2f}:1")
            print(f"  GMF (嚙合頻率): {GMF:.1f} Hz")
            print(f"干涉嚴重程度分數: {severity_score:.1f}/100")
        
        # 基本振幅設定
        base_amplitude = 1.0
        
        # 1. 基本旋轉頻率成分
        vibration_signal = (
            base_amplitude * 0.8 * np.sin(2 * np.pi * f_pinion * self.time) +  # 小齒輪基頻
            base_amplitude * 0.6 * np.sin(2 * np.pi * f_gear * self.time)      # 大齒輪基頻
        )
        
        # 2. 嚙合頻率及其諧波（更多諧波）
        mesh_harmonics = 8  # 增加到8個諧波
        for i in range(1, mesh_harmonics + 1):
            amp = base_amplitude * 0.5 * (1 / i)  # 諧波幅度遞減
            vibration_signal += amp * np.sin(2 * np.pi * GMF * i * self.time)
        
        # 3. 齒輪旋轉頻率諧波
        pinion_harmonics = 10  # 小齒輪10個諧波
        gear_harmonics = 10    # 大齒輪10個諧波
        
        # 小齒輪諧波
        for i in range(2, pinion_harmonics + 1):
            amp = base_amplitude * 0.3 * (1 / i)
            vibration_signal += amp * np.sin(2 * np.pi * f_pinion * i * self.time)
        
        # 大齒輪諧波
        for i in range(2, gear_harmonics + 1):
            amp = base_amplitude * 0.2 * (1 / i)
            vibration_signal += amp * np.sin(2 * np.pi * f_gear * i * self.time)
        
        # 4. 邊帶頻率（故障特徵）
        sideband_orders = 6  # 增加邊帶階數
        fault_multiplier = 1 + (severity_score / 100) * 5.0
        
        # 嚙合頻率邊帶
        for i in range(1, sideband_orders + 1):
            sideband_amp = base_amplitude * 0.1 * fault_multiplier * (1 / i)
            # 上邊帶
            vibration_signal += sideband_amp * np.sin(2 * np.pi * (GMF + i * f_pinion) * self.time)
            vibration_signal += sideband_amp * np.sin(2 * np.pi * (GMF + i * f_gear) * self.time)
            # 下邊帶
            vibration_signal += sideband_amp * np.sin(2 * np.pi * (GMF - i * f_pinion) * self.time)
            vibration_signal += sideband_amp * np.sin(2 * np.pi * (GMF - i * f_gear) * self.time)
        
        # 5. 故障頻率成分（基於干涉程度）
        vibration_signal = self._add_fault_components_enhanced(
            vibration_signal, severity_score, f_pinion, f_gear, GMF, fault_multiplier
        )
        
        # 6. 隨機噪音（基於嚴重程度）
        noise_base = 0.1
        noise_level = noise_base + (severity_score / 100) * 0.5
        noise = np.random.normal(0, noise_level, len(self.time))
        vibration_signal += noise
        if(DEBUG):
            print(f"故障倍增因子: {fault_multiplier:.2f}")
            print(f"噪音等級: {noise_level:.3f}")

        # 7. FFT分析（不計算相位）
        fft_results = self._perform_fft_analysis(vibration_signal)
        
        # 8. 計算特徵頻率
        characteristic_frequencies = self._calculate_characteristic_frequencies(
            f_pinion, f_gear, GMF, z_pinion, z_gear
        )
        
        return {
            'time': self.time,
            'vibration_signal': vibration_signal,
            'fft_freq': fft_results['freq'],
            'fft_magnitude': fft_results['magnitude'],
            'characteristic_frequencies': characteristic_frequencies,
            'severity_score': severity_score,
            'gear_parameters': {
                'f_pinion': f_pinion,
                'f_gear': f_gear,
                'GMF': GMF,
                'z_pinion': z_pinion,
                'z_gear': z_gear,
                'gear_ratio': gear_ratio
            },
            'simulation_params': {
                'rpm_pinion': rpm_pinion,
                'rpm_gear': rpm_gear,
                'noise_level': noise_level,
                'fault_multiplier': fault_multiplier,
                'sampling_rate': self.fs,
                'harmonics_count': {
                    'mesh': mesh_harmonics,
                    'pinion': pinion_harmonics,
                    'gear': gear_harmonics,
                    'sideband_orders': sideband_orders
                }
            }
        }
    
    def _add_fault_components_enhanced(self, signal, severity_score, f_pinion, f_gear, GMF, fault_multiplier):
        """
        增強版故障成分添加
        """
        base_amplitude = 1.0
        
        # 1. 沖擊成分（嚴重干涉時的衝擊）
        if severity_score > 50:
            impact_freq = GMF / 2  # 沖擊頻率
            impact_amp = base_amplitude * (severity_score / 100) * 0.8
            signal += impact_amp * np.sin(2 * np.pi * impact_freq * self.time) * np.exp(-2 * self.time)
        
        # 2. 調製成分（軸承故障模擬）
        modulation_freq = f_pinion * 0.4  # 軸承故障頻率
        modulation_amp = base_amplitude * 0.2 * fault_multiplier
        signal += modulation_amp * np.sin(2 * np.pi * modulation_freq * self.time) * np.sin(2 * np.pi * GMF * self.time)
        
        # 3. 不平衡成分
        unbalance_amp = base_amplitude * 0.3 * (severity_score / 100)
        signal += unbalance_amp * np.sin(2 * np.pi * f_pinion * self.time + np.pi/4)
        signal += unbalance_amp * 0.8 * np.sin(2 * np.pi * f_gear * self.time + np.pi/3)
        
        # 4. 對齊不良成分（2倍頻）
        misalign_amp = base_amplitude * 0.25 * (severity_score / 100)
        signal += misalign_amp * np.sin(2 * np.pi * 2 * f_pinion * self.time)
        signal += misalign_amp * 0.7 * np.sin(2 * np.pi * 2 * f_gear * self.time)
        
        # 5. 高頻調製（齒面缺陷）
        if severity_score > 30:
            tooth_defect_freq = GMF * 1.5
            defect_amp = base_amplitude * 0.15 * (severity_score / 100)
            signal += defect_amp * np.sin(2 * np.pi * tooth_defect_freq * self.time)
        
        return signal
    
    def _calculate_characteristic_frequencies(self, f_pinion, f_gear, GMF, z_pinion, z_gear):
        """
        計算特徵頻率
        """
        return {
            '基本頻率': {
                'f_pinion': f_pinion,
                'f_gear': f_gear,
                'GMF': GMF
            },
            '諧波頻率': {
                'pinion_harmonics': [f_pinion * i for i in range(1, 11)],
                'gear_harmonics': [f_gear * i for i in range(1, 11)],
                'mesh_harmonics': [GMF * i for i in range(1, 9)]
            },
            '邊帶頻率': {
                'mesh_plus_pinion': [GMF + i * f_pinion for i in range(1, 7)],
                'mesh_minus_pinion': [GMF - i * f_pinion for i in range(1, 7)],
                'mesh_plus_gear': [GMF + i * f_gear for i in range(1, 7)],
                'mesh_minus_gear': [GMF - i * f_gear for i in range(1, 7)]
            },
            '故障頻率': {
                'impact_freq': GMF / 2,
                'bearing_fault': f_pinion * 0.4,
                'misalignment_2x_pinion': 2 * f_pinion,
                'misalignment_2x_gear': 2 * f_gear,
                'tooth_defect': GMF * 1.5
            }
        }
    
    def _extract_severity_score(self, interference_analysis):
        """
        從干涉分析結果中提取嚴重程度分數
        """
        if 'severity' in interference_analysis:
            return interference_analysis['severity']['severity_score']
        
        # 舊版本相容性
        if 'overall_severity' in interference_analysis:
            return interference_analysis['overall_severity']
        
        # 基於統計數據計算
        stats = interference_analysis.get('statistics', {})
        if 'total_points' in stats and 'interference_points' in stats:
            interference_ratio = stats['interference_points'] / max(stats['total_points'], 1)
            return min(interference_ratio * 100, 100)
        
        return 0
    
    def _perform_fft_analysis(self, signal):
        """
        執行FFT分析（不計算相位）
        """
        # FFT計算
        fft_signal = np.fft.fft(signal)
        freqs = np.fft.fftfreq(len(signal), 1/self.fs)
        
        # 只取正頻率部分
        n = len(signal) // 2
        freqs = freqs[:n]
        magnitude = np.abs(fft_signal[:n]) * 2 / len(signal)
        
        return {
            'freq': freqs,
            'magnitude': magnitude
        }
    
    def plot_vibration_analysis(self, vibration_data, show_time_domain=True, show_frequency_domain=True):
        """
        繪製振動分析結果（移除相位圖）
        """
        fig_count = sum([show_time_domain, show_frequency_domain])
        if fig_count == 0:
            return None
        
        # 確定子圖行數
        rows = fig_count
        subplot_titles = []
        
        if show_time_domain:
            subplot_titles.append("時域振動信號")
        if show_frequency_domain:
            subplot_titles.append("頻域分析 (FFT) - 特徵頻率標記")
        
        fig = make_subplots(
            rows=rows, cols=1,
            subplot_titles=subplot_titles,
            vertical_spacing=0.15
        )
        
        current_row = 1
        
        # 時域圖
        if show_time_domain:
            fig.add_trace(
                go.Scatter(
                    x=vibration_data['time'][:2000],  # 只顯示前2000點以提高性能
                    y=vibration_data['vibration_signal'][:2000],
                    mode='lines',
                    name='振動信號',
                    line=dict(color='blue', width=1)
                ),
                row=current_row, col=1
            )
            fig.update_xaxes(title_text="時間 (s)", row=current_row, col=1)
            fig.update_yaxes(title_text="振幅", row=current_row, col=1)
            current_row += 1
        
        # 頻域圖
        if show_frequency_domain:
            # 限制頻率範圍到3000Hz以提高可讀性
            max_freq = 3000
            freq_mask = vibration_data['fft_freq'] <= max_freq
            
            fig.add_trace(
                go.Scatter(
                    x=vibration_data['fft_freq'][freq_mask],
                    y=vibration_data['fft_magnitude'][freq_mask],
                    mode='lines',
                    name='FFT振幅',
                    line=dict(color='red', width=1)
                ),
                row=current_row, col=1
            )
            
            # 標記特徵頻率
            self._add_frequency_markers(fig, vibration_data['characteristic_frequencies'], current_row)
            
            fig.update_xaxes(title_text="頻率 (Hz)", row=current_row, col=1)
            fig.update_yaxes(title_text="振幅", row=current_row, col=1)
        
        # 更新整體布局
        fig.update_layout(
            height=300 * rows,
            title=f"齒輪振動分析 (嚴重程度: {vibration_data['severity_score']:.1f}/100)",
            showlegend=True
        )
        
        return fig
    
    def _add_frequency_markers(self, fig, char_freqs, row):
        """
        在頻域圖上添加特徵頻率標記
        """
        # 標記主要頻率
        main_freqs = char_freqs['基本頻率']
        
        # 小齒輪頻率
        fig.add_vline(
            x=main_freqs['f_pinion'], 
            line_dash="dash", line_color="green",
            annotation_text=f"小齒輪 {main_freqs['f_pinion']:.1f}Hz",
            row=row, col=1
        )
        
        # 大齒輪頻率
        fig.add_vline(
            x=main_freqs['f_gear'], 
            line_dash="dash", line_color="orange",
            annotation_text=f"大齒輪 {main_freqs['f_gear']:.1f}Hz",
            row=row, col=1
        )
        
        # 嚙合頻率
        fig.add_vline(
            x=main_freqs['GMF'], 
            line_dash="dash", line_color="purple",
            annotation_text=f"嚙合 {main_freqs['GMF']:.1f}Hz",
            row=row, col=1
        )
        
        # 標記故障頻率
        fault_freqs = char_freqs['故障頻率']
        if fault_freqs['bearing_fault'] <= 3000:
            fig.add_vline(
                x=fault_freqs['bearing_fault'], 
                line_dash="dot", line_color="red",
                annotation_text=f"軸承故障 {fault_freqs['bearing_fault']:.1f}Hz",
                row=row, col=1
            )
    
    def export_vibration_data(self, vibration_data, filepath):
        """
        匯出振動數據到文件
        """
        import json
        
        # 準備可序列化的數據
        export_data = {
            'metadata': {
                'severity_score': vibration_data['severity_score'],
                'gear_parameters': vibration_data['gear_parameters'],
                'simulation_params': vibration_data['simulation_params'],
                'characteristic_frequencies': vibration_data['characteristic_frequencies']
            },
            'time_series': {
                'time': vibration_data['time'].tolist(),
                'vibration_signal': vibration_data['vibration_signal'].tolist()
            },
            'frequency_analysis': {
                'frequency': vibration_data['fft_freq'].tolist(),
                'magnitude': vibration_data['fft_magnitude'].tolist()
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"振動分析數據已匯出到: {filepath}")
        
    def print_analysis_summary(self, vibration_data):
        """
        打印分析摘要
        """
        print("\n=== 振動分析摘要 ===")
        print(f"嚴重程度分數: {vibration_data['severity_score']:.1f}/100")
        
        gear_params = vibration_data['gear_parameters']
        print(f"\n齒輪參數:")
        print(f"  小齒輪頻率: {gear_params['f_pinion']:.2f} Hz")
        print(f"  大齒輪頻率: {gear_params['f_gear']:.2f} Hz")
        print(f"  嚙合頻率: {gear_params['GMF']:.1f} Hz")
        print(f"  齒數比: {gear_params['gear_ratio']:.2f}:1")
        
        sim_params = vibration_data['simulation_params']
        print(f"\n模擬參數:")
        print(f"  取樣頻率: {sim_params['sampling_rate']} Hz")
        print(f"  噪音等級: {sim_params['noise_level']:.3f}")
        print(f"  故障倍增因子: {sim_params['fault_multiplier']:.2f}")
        
        harmonics = sim_params['harmonics_count']
        print(f"  諧波數量:")
        print(f"    嚙合諧波: {harmonics['mesh']}")
        print(f"    小齒輪諧波: {harmonics['pinion']}")
        print(f"    大齒輪諧波: {harmonics['gear']}")
        print(f"    邊帶階數: {harmonics['sideband_orders']}")
        
        # 頻域統計
        max_magnitude = np.max(vibration_data['fft_magnitude'])
        max_freq_idx = np.argmax(vibration_data['fft_magnitude'])
        dominant_freq = vibration_data['fft_freq'][max_freq_idx]
        
        print(f"\n頻域特徵:")
        print(f"  主導頻率: {dominant_freq:.1f} Hz")
        print(f"  最大振幅: {max_magnitude:.3f}")
        
        # 時域統計
        rms_value = np.sqrt(np.mean(vibration_data['vibration_signal']**2))
        peak_value = np.max(np.abs(vibration_data['vibration_signal']))
        crest_factor = peak_value / rms_value if rms_value > 0 else 0
        
        print(f"\n時域特徵:")
        print(f"  RMS值: {rms_value:.3f}")
        print(f"  峰值: {peak_value:.3f}")
        print(f"  峰值因子: {crest_factor:.2f}")
        print("=" * 30)

"""
振動數據分析器
用於讀取和分析儲存的NPZ振動數據
"""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime

class VibrationDataAnalyzer:
    def __init__(self, tmp_path=None):
        """
        初始化振動數據分析器
        
        Args:
            tmp_path: NPZ文件儲存路徑，預設為當前專案的tmp資料夾
        """
        if tmp_path is None:
            # 自動偵測專案路徑
            current_dir = os.path.dirname(os.path.abspath(__file__))
            tmp_path = os.path.join(current_dir, "tmp")
        
        self.tmp_path = tmp_path
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
        
    def save_vibration_data(self, vibration_data, filename_prefix="vibration"):
        """
        儲存振動數據到NPZ文件
        
        Args:
            vibration_data: 振動分析結果
            filename_prefix: 文件名前綴
            
        Returns:
            str: 儲存的文件路徑
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.npz"
        filepath = os.path.join(self.tmp_path, filename)
        
        # 準備要儲存的數據
        save_data = {
            'time': vibration_data['time'],
            'vibration_signal': vibration_data['vibration_signal'],
            'fft_freq': vibration_data['fft_freq'],
            'fft_magnitude': vibration_data['fft_magnitude'],
            'severity_score': vibration_data['severity_score']
        }
        
        # 儲存gear_parameters
        gear_params = vibration_data['gear_parameters']
        for key, value in gear_params.items():
            save_data[f"gear_{key}"] = value
        
        # 儲存simulation_params
        sim_params = vibration_data['simulation_params']
        for key, value in sim_params.items():
            if isinstance(value, dict):
                # 處理巢狀字典
                for sub_key, sub_value in value.items():
                    save_data[f"sim_{key}_{sub_key}"] = sub_value
            else:
                save_data[f"sim_{key}"] = value
        
        # 儲存特徵頻率
        char_freqs = vibration_data['characteristic_frequencies']
        save_data['char_freqs_json'] = json.dumps(char_freqs, ensure_ascii=False)
        
        np.savez_compressed(filepath, **save_data)
        print(f"✅ 振動數據已儲存到: {filepath}")
        return filepath
    
    def load_vibration_data(self, filepath):
        """
        從NPZ文件載入振動數據
        
        Args:
            filepath: NPZ文件路徑
            
        Returns:
            dict: 振動數據
        """
        try:
            data = np.load(filepath, allow_pickle=True)
            
            # 重建原始數據結構
            vibration_data = {
                'time': data['time'],
                'vibration_signal': data['vibration_signal'],
                'fft_freq': data['fft_freq'],
                'fft_magnitude': data['fft_magnitude'],
                'severity_score': float(data['severity_score']),
                'gear_parameters': {},
                'simulation_params': {},
                'characteristic_frequencies': {}
            }
            
            # 重建gear_parameters
            for key in data.files:
                if key.startswith('gear_'):
                    param_name = key[5:]  # 移除'gear_'前綴
                    vibration_data['gear_parameters'][param_name] = float(data[key])
                elif key.startswith('sim_'):
                    # 處理simulation_params
                    param_parts = key[4:].split('_', 1)  # 移除'sim_'前綴
                    if len(param_parts) == 2:
                        main_key, sub_key = param_parts
                        if main_key not in vibration_data['simulation_params']:
                            vibration_data['simulation_params'][main_key] = {}
                        vibration_data['simulation_params'][main_key][sub_key] = float(data[key])
                    else:
                        vibration_data['simulation_params'][param_parts[0]] = float(data[key])
            
            # 重建characteristic_frequencies
            if 'char_freqs_json' in data.files:
                vibration_data['characteristic_frequencies'] = json.loads(str(data['char_freqs_json']))
            
            print(f"✅ 振動數據載入成功: {filepath}")
            return vibration_data
            
        except Exception as e:
            print(f"❌ 載入振動數據失敗: {e}")
            return None
    
    def list_saved_files(self):
        """
        列出tmp資料夾中的所有NPZ文件
        
        Returns:
            list: 文件列表
        """
        try:
            files = [f for f in os.listdir(self.tmp_path) if f.endswith('.npz')]
            files.sort(reverse=True)  # 最新的在前面
            
            print(f"📁 tmp資料夾中的振動數據文件 ({len(files)}個):")
            for i, filename in enumerate(files):
                filepath = os.path.join(self.tmp_path, filename)
                size = os.path.getsize(filepath) / 1024  # KB
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                print(f"  {i+1}. {filename} ({size:.1f}KB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
            
            return files
            
        except Exception as e:
            print(f"❌ 列出文件失敗: {e}")
            return []
    
    def compare_vibration_data(self, filepaths):
        """
        比較多個振動數據文件，專注於GMF能量、旁波分析和高頻諧波
        
        Args:
            filepaths: 文件路徑列表
        """
        if len(filepaths) < 2:
            print("⚠️ 需要至少2個文件進行比較")
            return

        data_list = []
        labels = []
        
        for filepath in filepaths:
            data = self.load_vibration_data(filepath)
            if data:
                data_list.append(data)
                filename = os.path.basename(filepath)
                labels.append(f"{filename[:20]}... (嚴重度:{data['severity_score']:.1f})")

        if len(data_list) < 2:
            print("❌ 無法載入足夠的數據進行比較")
            return

        # 提取GMF和諧波分析數據
        gmf_analysis = self._analyze_gmf_harmonics(data_list, labels)
        
        # 創建增強版比較圖表
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'GMF基頻能量比較', 'GMF諧波能量分布', 
                'GMF旁波分析', '高頻諧波能量',
                'FFT頻譜比較 (0-2000Hz)', '齒輪故障特徵頻率'
            ),
            specs=[[{}, {}], [{}, {}], [{}, {}]],
            row_heights=[0.25, 0.25, 0.5]
        )
        
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        
        # 1. GMF基頻能量比較
        gmf_energies = [analysis['gmf_energy'] for analysis in gmf_analysis]
        fig.add_trace(
            go.Bar(
                x=labels,
                y=gmf_energies,
                name='GMF能量',
                marker_color=colors[:len(data_list)],
                showlegend=False
            ),
            row=1, col=1
        )
        
        # 2. GMF諧波能量分布
        harmonic_numbers = list(range(1, 11))  # 顯示前10個諧波
        for i, (analysis, label) in enumerate(zip(gmf_analysis, labels)):
            fig.add_trace(
                go.Scatter(
                    x=harmonic_numbers,
                    y=analysis['harmonic_energies'][:10],
                    mode='lines+markers',
                    name=f'{label[:10]}...',
                    line=dict(color=colors[i % len(colors)]),
                    marker=dict(size=6)
                ),
                row=1, col=2
            )
        
        # 3. GMF旁波分析
        for i, (analysis, label) in enumerate(zip(gmf_analysis, labels)):
            sideband_freqs = analysis['sideband_freqs']
            sideband_energies = analysis['sideband_energies']
            
            fig.add_trace(
                go.Scatter(
                    x=sideband_freqs,
                    y=sideband_energies,
                    mode='markers',
                    name=f'{label[:10]}... 旁波',
                    marker=dict(color=colors[i % len(colors)], size=8, symbol='diamond'),
                    showlegend=False
                ),
                row=2, col=1
            )
        
        # 4. 高頻諧波能量
        high_freq_analysis = self._analyze_high_frequency_harmonics(data_list, labels)
        for i, (analysis, label) in enumerate(zip(high_freq_analysis, labels)):
            fig.add_trace(
                go.Bar(
                    x=[f'H{j+1}' for j in range(len(analysis['high_freq_energies']))],
                    y=analysis['high_freq_energies'],
                    name=f'{label[:10]}... 高頻',
                    marker_color=colors[i % len(colors)],
                    opacity=0.7,
                    showlegend=False
                ),
                row=2, col=2
            )
        
        # 5. FFT頻譜比較 (0-2000Hz)
        for i, (data, label) in enumerate(zip(data_list, labels)):
            color = colors[i % len(colors)]
            freq_mask = data['fft_freq'] <= 2000
            fig.add_trace(
                go.Scatter(
                    x=data['fft_freq'][freq_mask],
                    y=data['fft_magnitude'][freq_mask],
                    mode='lines',
                    name=f'{label[:10]}... 頻譜',
                    line=dict(color=color, width=1.5),
                    showlegend=False
                ),
                row=3, col=1
            )
            
            # 添加重要頻率標記，避免標籤重疊
            if 'gear_parameters' in data:
                gear_params = data['gear_parameters']
                gmf_freq = gear_params.get('GMF', 600)
                f_pinion = gear_params.get('f_pinion', 30)
                f_gear = gear_params.get('f_gear', 10)
                
                # 只標記GMF頻率，避免小齒輪和大齒輪頻率標籤重疊
                gmf_idx = np.argmin(np.abs(data['fft_freq'] - gmf_freq))
                gmf_amplitude = data['fft_magnitude'][gmf_idx]
                
                # 添加GMF標記
                fig.add_trace(
                    go.Scatter(
                        x=[gmf_freq],
                        y=[gmf_amplitude],
                        mode='markers+text',
                        marker=dict(color=color, size=10, symbol='star'),
                        text=[f'GMF:{gmf_freq:.0f}Hz'],
                        textposition='top center',
                        textfont=dict(size=10, color=color),
                        showlegend=False,
                        hovertemplate=f'GMF: {gmf_freq:.1f}Hz<br>振幅: {gmf_amplitude:.3f}<extra></extra>'
                    ),
                    row=3, col=1
                )
                
                # 如果小齒輪和大齒輪頻率差距夠大，才分別標記
                freq_diff = abs(f_pinion - f_gear)
                if freq_diff > 10:  # 頻率差超過10Hz才分別標記
                    # 標記小齒輪頻率
                    pinion_idx = np.argmin(np.abs(data['fft_freq'] - f_pinion))
                    pinion_amplitude = data['fft_magnitude'][pinion_idx]
                    
                    fig.add_trace(
                        go.Scatter(
                            x=[f_pinion],
                            y=[pinion_amplitude],
                            mode='markers+text',
                            marker=dict(color=color, size=8, symbol='triangle-up'),
                            text=[f'P:{f_pinion:.0f}'],
                            textposition='top right',
                            textfont=dict(size=9, color=color),
                            showlegend=False,
                            hovertemplate=f'小齒輪: {f_pinion:.1f}Hz<br>振幅: {pinion_amplitude:.3f}<extra></extra>'
                        ),
                        row=3, col=1
                    )
                    
                    # 標記大齒輪頻率
                    gear_idx = np.argmin(np.abs(data['fft_freq'] - f_gear))
                    gear_amplitude = data['fft_magnitude'][gear_idx]
                    
                    fig.add_trace(
                        go.Scatter(
                            x=[f_gear],
                            y=[gear_amplitude],
                            mode='markers+text',
                            marker=dict(color=color, size=8, symbol='triangle-down'),
                            text=[f'G:{f_gear:.0f}'],
                            textposition='bottom right',
                            textfont=dict(size=9, color=color),
                            showlegend=False,
                            hovertemplate=f'大齒輪: {f_gear:.1f}Hz<br>振幅: {gear_amplitude:.3f}<extra></extra>'
                        ),
                        row=3, col=1
                    )
                else:
                    # 頻率太接近時，使用組合標記
                    avg_freq = (f_pinion + f_gear) / 2
                    avg_idx = np.argmin(np.abs(data['fft_freq'] - avg_freq))
                    avg_amplitude = data['fft_magnitude'][avg_idx]
                    
                    fig.add_trace(
                        go.Scatter(
                            x=[avg_freq],
                            y=[avg_amplitude],
                            mode='markers+text',
                            marker=dict(color=color, size=8, symbol='circle'),
                            text=[f'P/G:{f_pinion:.0f}/{f_gear:.0f}'],
                            textposition='top left',
                            textfont=dict(size=9, color=color),
                            showlegend=False,
                            hovertemplate=f'齒輪頻率<br>小齒輪: {f_pinion:.1f}Hz<br>大齒輪: {f_gear:.1f}Hz<br>振幅: {avg_amplitude:.3f}<extra></extra>'
                        ),
                        row=3, col=1
                    )
        
        # 6. 齒輪故障特徵頻率
        fault_freq_analysis = self._analyze_fault_frequencies(data_list, labels)
        for i, (analysis, label) in enumerate(zip(fault_freq_analysis, labels)):
            fig.add_trace(
                go.Scatter(
                    x=['GMF', 'BPFI', 'BPFO', 'BSF', 'FTF'],
                    y=[
                        analysis['gmf_amplitude'],
                        analysis['bearing_inner_amp'],
                        analysis['bearing_outer_amp'],
                        analysis['ball_spin_amp'],
                        analysis['cage_amp']
                    ],
                    mode='markers+lines',
                    name=f'{label[:10]}... 故障',
                    marker=dict(color=colors[i % len(colors)], size=8),
                    showlegend=False
                ),
                row=3, col=2
            )
        
        # 更新布局
        fig.update_layout(
            height=1200,
            title="增強版振動數據比較分析 - GMF/諧波/旁波重點分析",
            showlegend=True
        )
        
        # 更新坐標軸標籤
        fig.update_xaxes(title_text="數據文件", row=1, col=1)
        fig.update_yaxes(title_text="GMF能量", row=1, col=1)
        
        fig.update_xaxes(title_text="諧波次數", row=1, col=2)
        fig.update_yaxes(title_text="諧波能量", row=1, col=2)
        
        fig.update_xaxes(title_text="頻率 (Hz)", row=2, col=1)
        fig.update_yaxes(title_text="旁波能量", row=2, col=1)
        
        fig.update_xaxes(title_text="高頻諧波", row=2, col=2)
        fig.update_yaxes(title_text="能量", row=2, col=2)
        
        fig.update_xaxes(title_text="頻率 (Hz)", row=3, col=1)
        fig.update_yaxes(title_text="振幅", row=3, col=1)
        
        fig.update_xaxes(title_text="故障頻率類型", row=3, col=2)
        fig.update_yaxes(title_text="振幅", row=3, col=2)
        
        fig.show()
        
        # 顯示詳細的GMF和諧波比較分析
        self._print_detailed_gmf_analysis(gmf_analysis, labels)
    
    def _analyze_gmf_harmonics(self, data_list, labels):
        """分析GMF基頻和諧波能量"""
        analysis_results = []
        
        for data in data_list:
            result = {
                'gmf_energy': 0,
                'harmonic_energies': [],
                'sideband_freqs': [],
                'sideband_energies': []
            }
            
            if 'gear_parameters' not in data:
                analysis_results.append(result)
                continue
                
            gmf_freq = data['gear_parameters'].get('GMF', 600)  # 默認600Hz
            freq_array = data['fft_freq']
            magnitude_array = data['fft_magnitude']
            
            # 分析GMF基頻能量
            gmf_idx = np.argmin(np.abs(freq_array - gmf_freq))
            tolerance = 5  # ±5Hz容忍度
            gmf_mask = np.abs(freq_array - gmf_freq) <= tolerance
            result['gmf_energy'] = np.sum(magnitude_array[gmf_mask]**2)
            
            # 分析GMF諧波能量 (2×GMF, 3×GMF, ...)
            harmonic_energies = []
            for harmonic in range(1, 16):  # 分析前15個諧波
                harmonic_freq = gmf_freq * harmonic
                if harmonic_freq > np.max(freq_array):
                    break
                harmonic_idx = np.argmin(np.abs(freq_array - harmonic_freq))
                harmonic_mask = np.abs(freq_array - harmonic_freq) <= tolerance
                harmonic_energy = np.sum(magnitude_array[harmonic_mask]**2)
                harmonic_energies.append(harmonic_energy)
            
            result['harmonic_energies'] = harmonic_energies
            
            # 分析GMF旁波 (GMF ± 轉速頻率)
            f_pinion = data['gear_parameters'].get('f_pinion', 30)
            f_gear = data['gear_parameters'].get('f_gear', 10)
            
            # 檢查GMF周圍的旁波
            for sideband_offset in [f_pinion, f_gear, f_pinion/2, f_gear/2]:
                for sign in [-1, 1]:
                    sideband_freq = gmf_freq + sign * sideband_offset
                    if 0 < sideband_freq < np.max(freq_array):
                        sideband_idx = np.argmin(np.abs(freq_array - sideband_freq))
                        sideband_energy = magnitude_array[sideband_idx]**2
                        result['sideband_freqs'].append(sideband_freq)
                        result['sideband_energies'].append(sideband_energy)
            
            analysis_results.append(result)
        
        return analysis_results
    
    def _analyze_high_frequency_harmonics(self, data_list, labels):
        """分析高頻諧波能量分布"""
        analysis_results = []
        
        for data in data_list:
            result = {'high_freq_energies': []}
            
            freq_array = data['fft_freq']
            magnitude_array = data['fft_magnitude']
            
            # 分析1000Hz以上的高頻段能量分布
            high_freq_bands = [
                (1000, 1500), (1500, 2000), (2000, 3000), 
                (3000, 4000), (4000, 5000), (5000, 6000)
            ]
            
            for freq_min, freq_max in high_freq_bands:
                band_mask = (freq_array >= freq_min) & (freq_array < freq_max)
                if np.any(band_mask):
                    band_energy = np.sum(magnitude_array[band_mask]**2)
                    result['high_freq_energies'].append(band_energy)
                else:
                    result['high_freq_energies'].append(0)
            
            analysis_results.append(result)
        
        return analysis_results
    
    def _analyze_fault_frequencies(self, data_list, labels):
        """分析齒輪和軸承故障特徵頻率"""
        analysis_results = []
        
        for data in data_list:
            result = {
                'gmf_amplitude': 0,
                'bearing_inner_amp': 0,
                'bearing_outer_amp': 0,
                'ball_spin_amp': 0,
                'cage_amp': 0
            }
            
            if 'gear_parameters' not in data:
                analysis_results.append(result)
                continue
                
            freq_array = data['fft_freq']
            magnitude_array = data['fft_magnitude']
            
            # GMF振幅
            gmf_freq = data['gear_parameters'].get('GMF', 600)
            gmf_idx = np.argmin(np.abs(freq_array - gmf_freq))
            result['gmf_amplitude'] = magnitude_array[gmf_idx]
            
            # 軸承故障頻率 (基於典型軸承參數估算)
            f_shaft = data['gear_parameters'].get('f_pinion', 30)  # 軸頻率
            
            # 內圈故障頻率 (BPFI)
            bpfi_freq = f_shaft * 6.5  # 假設軸承內圈故障頻率約為軸頻率的6.5倍
            if bpfi_freq < np.max(freq_array):
                bpfi_idx = np.argmin(np.abs(freq_array - bpfi_freq))
                result['bearing_inner_amp'] = magnitude_array[bpfi_idx]
            
            # 外圈故障頻率 (BPFO)
            bpfo_freq = f_shaft * 4.5  # 假設軸承外圈故障頻率約為軸頻率的4.5倍
            if bpfo_freq < np.max(freq_array):
                bpfo_idx = np.argmin(np.abs(freq_array - bpfo_freq))
                result['bearing_outer_amp'] = magnitude_array[bpfo_idx]
            
            # 滾珠自轉頻率 (BSF)
            bsf_freq = f_shaft * 2.3  # 假設滾珠自轉頻率約為軸頻率的2.3倍
            if bsf_freq < np.max(freq_array):
                bsf_idx = np.argmin(np.abs(freq_array - bsf_freq))
                result['ball_spin_amp'] = magnitude_array[bsf_idx]
            
            # 保持架故障頻率 (FTF)
            ftf_freq = f_shaft * 0.4  # 假設保持架故障頻率約為軸頻率的0.4倍
            if ftf_freq < np.max(freq_array):
                ftf_idx = np.argmin(np.abs(freq_array - ftf_freq))
                result['cage_amp'] = magnitude_array[ftf_idx]
            
            analysis_results.append(result)
        
        return analysis_results
    
    def _print_detailed_gmf_analysis(self, gmf_analysis, labels):
        """顯示詳細的GMF和諧波分析結果"""
        print(f"\n🔧 GMF與諧波詳細分析報告")
        print("=" * 80)
        
        # GMF基頻能量比較
        print(f"\n📊 GMF基頻能量比較:")
        print(f"{'文件':<30} {'GMF能量':<15} {'能量等級':<10}")
        print("-" * 55)
        
        max_gmf_energy = max([analysis['gmf_energy'] for analysis in gmf_analysis])
        
        for analysis, label in zip(gmf_analysis, labels):
            energy_ratio = analysis['gmf_energy'] / max_gmf_energy if max_gmf_energy > 0 else 0
            energy_level = "高" if energy_ratio > 0.7 else "中" if energy_ratio > 0.3 else "低"
            print(f"{label[:29]:<30} {analysis['gmf_energy']:<15.6f} {energy_level:<10}")
        
        # 諧波能量分布比較
        print(f"\n🎵 GMF諧波能量分布比較:")
        print(f"{'文件':<20} {'1×GMF':<10} {'2×GMF':<10} {'3×GMF':<10} {'4×GMF':<10} {'5×GMF':<10}")
        print("-" * 70)
        
        for analysis, label in zip(gmf_analysis, labels):
            harmonics = analysis['harmonic_energies'][:5]  # 顯示前5個諧波
            while len(harmonics) < 5:
                harmonics.append(0)  # 補零
            
            print(f"{label[:19]:<20} {harmonics[0]:<10.4f} {harmonics[1]:<10.4f} "
                  f"{harmonics[2]:<10.4f} {harmonics[3]:<10.4f} {harmonics[4]:<10.4f}")
        
        # 旁波分析
        print(f"\n🌊 GMF旁波分析:")
        for i, (analysis, label) in enumerate(zip(gmf_analysis, labels)):
            if analysis['sideband_energies']:
                print(f"\n{label[:30]}:")
                sideband_count = len(analysis['sideband_energies'])
                total_sideband_energy = sum(analysis['sideband_energies'])
                avg_sideband_energy = total_sideband_energy / sideband_count if sideband_count > 0 else 0
                
                print(f"  旁波數量: {sideband_count}")
                print(f"  平均旁波能量: {avg_sideband_energy:.6f}")
                print(f"  旁波/GMF比: {avg_sideband_energy/analysis['gmf_energy']:.3f}" if analysis['gmf_energy'] > 0 else "  旁波/GMF比: N/A")
        
        # 診斷建議
        print(f"\n💡 齒輪診斷建議:")
        for analysis, label in zip(gmf_analysis, labels):
            print(f"\n{label[:30]}:")
            
            # GMF能量診斷
            if analysis['gmf_energy'] > max_gmf_energy * 0.7:
                print("  ✅ GMF能量正常")
            elif analysis['gmf_energy'] > max_gmf_energy * 0.3:
                print("  ⚠️ GMF能量中等，建議監控")
            else:
                print("  ❌ GMF能量偏低，可能存在嚙合問題")
            
            # 諧波診斷
            if len(analysis['harmonic_energies']) >= 2:
                harmonic_ratio = analysis['harmonic_energies'][1] / analysis['harmonic_energies'][0] if analysis['harmonic_energies'][0] > 0 else 0
                if harmonic_ratio > 0.5:
                    print("  ❌ 2×GMF諧波過高，可能存在齒面磨損")
                elif harmonic_ratio > 0.2:
                    print("  ⚠️ 2×GMF諧波中等，建議檢查齒面狀況")
                else:
                    print("  ✅ 諧波分布正常")
            
            # 旁波診斷
            if analysis['sideband_energies']:
                avg_sideband = sum(analysis['sideband_energies']) / len(analysis['sideband_energies'])
                sideband_ratio = avg_sideband / analysis['gmf_energy'] if analysis['gmf_energy'] > 0 else 0
                
                if sideband_ratio > 0.3:
                    print("  ❌ 旁波明顯，可能存在調變問題或不對中")
                elif sideband_ratio > 0.1:
                    print("  ⚠️ 旁波中等，建議檢查軸對中")
                else:
                    print("  ✅ 旁波正常")

    def analyze_single_file(self, filepath):
        """
        分析單個振動數據文件
        
        Args:
            filepath: NPZ文件路徑
        """
        data = self.load_vibration_data(filepath)
        if not data:
            return
        
        print(f"\n📊 振動數據分析報告")
        print(f"文件: {os.path.basename(filepath)}")
        print("=" * 50)
        
        # 基本信息
        print(f"嚴重程度分數: {data['severity_score']:.1f}/100")
        
        # 齒輪參數
        if 'gear_parameters' in data:
            gear_params = data['gear_parameters']
            print(f"\n齒輪參數:")
            print(f"  小齒輪頻率: {gear_params.get('f_pinion', 0):.2f} Hz")
            print(f"  大齒輪頻率: {gear_params.get('f_gear', 0):.2f} Hz")
            print(f"  嚙合頻率: {gear_params.get('f_mesh', 0):.1f} Hz")
            print(f"  齒數比: {gear_params.get('gear_ratio', 0):.2f}:1")
        
        # 時域統計
        signal = data['vibration_signal']
        rms_value = np.sqrt(np.mean(signal**2))
        peak_value = np.max(np.abs(signal))
        crest_factor = peak_value / rms_value if rms_value > 0 else 0
        
        print(f"\n時域特徵:")
        print(f"  RMS值: {rms_value:.3f}")
        print(f"  峰值: {peak_value:.3f}")
        print(f"  峰值因子: {crest_factor:.2f}")
        
        # 頻域特徵
        max_magnitude = np.max(data['fft_magnitude'])
        max_freq_idx = np.argmax(data['fft_magnitude'])
        dominant_freq = data['fft_freq'][max_freq_idx]
        
        print(f"\n頻域特徵:")
        print(f"  主導頻率: {dominant_freq:.1f} Hz")
        print(f"  最大振幅: {max_magnitude:.3f}")
        
        # 模擬參數
        if 'simulation_params' in data:
            sim_params = data['simulation_params']
            print(f"\n模擬參數:")
            print(f"  取樣頻率: {sim_params.get('sampling_rate', 0)} Hz")
            print(f"  故障倍增因子: {sim_params.get('fault_multiplier', 0):.2f}")
            print(f"  噪音等級: {sim_params.get('noise_level', 0):.3f}")
        
        return data

# 全域函數，方便在notebook中使用
def get_vibration_analyzer():
    """取得振動數據分析器實例"""
    return VibrationDataAnalyzer()

def quick_load_latest():
    """快速載入最新的振動數據"""
    analyzer = VibrationDataAnalyzer()
    files = analyzer.list_saved_files()
    if files:
        latest_file = os.path.join(analyzer.tmp_path, files[0])
        return analyzer.analyze_single_file(latest_file)
    else:
        print("📂 tmp資料夾中沒有振動數據文件")
        return None

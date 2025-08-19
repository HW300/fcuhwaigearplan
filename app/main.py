#!/usr/bin/env python3
"""
齒輪分析主程式 (Python腳本版本)

本程式提供齒輪干涉分析和FFT振動模擬功能
可通過命令列參數或互動模式使用
"""

import sys
import os
import argparse
import numpy as np
import json
from datetime import datetime

# 添加專案路徑
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_path)

# 匯入自定義模組
from geometry.gear_loader import GearLoader
from geometry.gear_transformer import GearTransformer
from visualization.gear_visualizer import GearVisualizer
from analysis.gear_interference_analyzer import GearInterferenceAnalyzer
from simulation.gear_vibration_simulator import GearVibrationSimulator

class GearAnalysisEngine:
    """齒輪分析引擎"""
    
    def __init__(self, stl_path=None):
        """初始化分析引擎"""
        if stl_path is None:
            stl_path = os.path.dirname(project_path)  # 回到上層目錄
        
        self.loader = GearLoader(stl_path)
        self.transformer = GearTransformer()
        self.visualizer = GearVisualizer()
        self.analyzer = GearInterferenceAnalyzer()
        self.vibration_sim = GearVibrationSimulator()
        
        # 載入齒輪模型
        self.pinion_mesh = None
        self.gear_mesh = None
        self.current_analysis = None
        
    def initialize(self):
        """初始化齒輪模型"""
        print("🔧 初始化齒輪分析引擎...")
        
        # 載入STL檔案
        self.pinion_mesh, self.gear_mesh = self.loader.load_stl_files()
        
        if self.pinion_mesh is None or self.gear_mesh is None:
            raise RuntimeError("無法載入齒輪STL檔案")
        
        # 設置變換器
        self.transformer.setup_gears(self.pinion_mesh, self.gear_mesh)
        print("✅ 齒輪模型初始化完成")
        
        return True
    
    def analyze_gear_position(self, x_distance=0, y_distance=-31, 
                            manual_offset_deg=10.0, sample_rate=5,
                            show_plots=True, save_plots=False):
        """
        分析特定齒輪位置的干涉情況
        
        Args:
            x_distance: X方向距離（小齒輪移動）
            y_distance: Y方向距離（大齒輪移動）
            manual_offset_deg: 旋轉偏移角度
            sample_rate: 分析取樣率
            show_plots: 是否顯示圖表
            save_plots: 是否保存圖表
            
        Returns:
            dict: 分析結果
        """
        print(f"🔍 分析齒輪位置: X={x_distance}, Y={y_distance}, 偏移={manual_offset_deg}°")
        
        try:
            # 重置齒輪到原始狀態
            self.transformer.reset_gears()
            
            # 執行變換
            vp, fp, vg, fg, transform_info = self.transformer.transform_gears(
                x_distance=x_distance,
                y_distance=y_distance,
                manual_offset_deg=manual_offset_deg
            )
            
            # 執行干涉分析
            print("📊 執行干涉分析...")
            self.current_analysis = self.analyzer.analyze_interference(
                vp, fp, vg, fg, sample_rate=sample_rate
            )
            
            # 合併分析結果
            analysis_result = {
                'position': {
                    'x_distance': x_distance,
                    'y_distance': y_distance,
                    'manual_offset_deg': manual_offset_deg
                },
                'transform_info': transform_info,
                'interference_analysis': self.current_analysis,
                'severity_score': self.analyzer.get_interference_severity_score()
            }
            
            # 可視化
            if show_plots:
                self._create_visualizations(vp, fp, vg, fg, transform_info, save_plots)
            
            print(f"✅ 分析完成！嚴重程度分數: {analysis_result['severity_score']:.2f}")
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ 分析過程中發生錯誤: {e}")
            raise
    
    def simulate_vibration(self, rpm_pinion=1800, rpm_gear=1800, 
                          show_plots=True, save_plots=False, export_data=True):
        """
        模擬振動信號
        
        Args:
            rpm_pinion: 小齒輪轉速
            rpm_gear: 大齒輪轉速
            show_plots: 是否顯示圖表
            save_plots: 是否保存圖表
            export_data: 是否匯出資料
            
        Returns:
            dict: 振動分析結果
        """
        if self.current_analysis is None:
            raise RuntimeError("請先執行齒輪位置分析")
        
        print(f"📊 模擬振動信號 (小齒輪: {rpm_pinion} RPM, 大齒輪: {rpm_gear} RPM)")
        
        try:
            # 模擬振動信號
            vibration_data = self.vibration_sim.simulate_vibration_signal(
                self.current_analysis,
                rpm_pinion=rpm_pinion,
                rpm_gear=rpm_gear
            )
            
            # 可視化
            if show_plots:
                fig = self.vibration_sim.create_vibration_plots(vibration_data)
                if save_plots:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"vibration_analysis_{timestamp}.html"
                    fig.write_html(filename)
                    print(f"📁 振動分析圖表已保存: {filename}")
                else:
                    fig.show()
            
            # 匯出資料
            if export_data:
                pos = self.current_analysis.get('position', {})
                x_val = pos.get('x_distance', 0)
                y_val = pos.get('y_distance', 0)
                filename = f"vibration_x{x_val}_y{y_val}.npz"
                self.vibration_sim.export_vibration_data(vibration_data, filename)
            
            print("✅ 振動分析完成！")
            return vibration_data
            
        except Exception as e:
            print(f"❌ 振動分析過程中發生錯誤: {e}")
            raise
    
    def batch_analysis(self, x_range, y_range, step=5, save_results=True):
        """
        批次分析多個位置組合
        
        Args:
            x_range: X軸範圍 (min, max)
            y_range: Y軸範圍 (min, max)
            step: 步長
            save_results: 是否保存結果
            
        Returns:
            list: 批次分析結果
        """
        print(f"🔄 開始批次分析...")
        print(f"X範圍: {x_range}, Y範圍: {y_range}, 步長: {step}")
        
        results = []
        x_values = np.arange(x_range[0], x_range[1] + step, step)
        y_values = np.arange(y_range[0], y_range[1] + step, step)
        
        total_combinations = len(x_values) * len(y_values)
        print(f"總計 {total_combinations} 個位置組合")
        
        for i, x_dist in enumerate(x_values):
            for j, y_dist in enumerate(y_values):
                try:
                    # 快速分析（不顯示圖表）
                    result = self.analyze_gear_position(
                        x_distance=x_dist, 
                        y_distance=y_dist,
                        sample_rate=10,  # 使用較高取樣率以提升速度
                        show_plots=False
                    )
                    
                    # 簡化結果
                    simplified_result = {
                        'x_distance': x_dist,
                        'y_distance': y_dist,
                        'center_distance': result['transform_info']['center_distance'],
                        'severity_score': result['severity_score'],
                        'total_interference': result['interference_analysis']['statistics']['total_interference_points'],
                        'total_contact': result['interference_analysis']['statistics']['total_contact_points']
                    }
                    
                    results.append(simplified_result)
                    
                    # 進度顯示
                    progress = ((i * len(y_values) + j + 1) / total_combinations) * 100
                    if (i * len(y_values) + j + 1) % 10 == 0:
                        print(f"進度: {progress:.1f}% - X:{x_dist}, Y:{y_dist}, 嚴重度:{simplified_result['severity_score']:.1f}")
                    
                except Exception as e:
                    print(f"⚠️ 分析 X:{x_dist}, Y:{y_dist} 時發生錯誤: {e}")
                    continue
        
        # 保存結果
        if save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_analysis_{timestamp}.json"
            
            # 轉換numpy類型為Python原生類型
            serializable_results = []
            for result in results:
                serializable_result = {}
                for key, value in result.items():
                    if isinstance(value, np.integer):
                        serializable_result[key] = int(value)
                    elif isinstance(value, np.floating):
                        serializable_result[key] = float(value)
                    else:
                        serializable_result[key] = value
                serializable_results.append(serializable_result)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
            print(f"📁 批次分析結果已保存: {filename}")
        
        # 找出最佳位置
        if results:
            min_severity_idx = np.argmin([r['severity_score'] for r in results])
            best_result = results[min_severity_idx]
            
            print(f"\n🏆 最佳位置組合:")
            print(f"X距離: {best_result['x_distance']}")
            print(f"Y距離: {best_result['y_distance']}")
            print(f"嚴重程度分數: {best_result['severity_score']:.2f}")
            print(f"中心距離: {best_result['center_distance']:.2f} mm")
        
        print(f"✅ 批次分析完成！共分析 {len(results)} 個位置")
        return results
    
    def _create_visualizations(self, vp, fp, vg, fg, transform_info, save_plots=False):
        """創建可視化圖表"""
        try:
            # 基本可視化
            fig1 = self.visualizer.create_basic_visualization(vp, fp, vg, fg, transform_info)
            
            # 干涉可視化
            self.visualizer.add_interference_visualization(
                self.current_analysis['interference_points']
            )
            
            if save_plots:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename1 = f"gear_analysis_{timestamp}.html"
                fig1.write_html(filename1)
                
                filename2 = f"interference_analysis_{timestamp}.html"
                self.visualizer.fig.write_html(filename2)
                
                print(f"📁 分析圖表已保存: {filename1}, {filename2}")
            else:
                fig1.show()
                self.visualizer.fig.show()
                
        except Exception as e:
            print(f"⚠️ 可視化過程中發生錯誤: {e}")

def interactive_mode():
    """互動模式"""
    print("=" * 60)
    print("🦷 齒輪分析系統 - 互動模式")
    print("=" * 60)
    
    # 初始化引擎
    engine = GearAnalysisEngine()
    try:
        engine.initialize()
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        return
    
    while True:
        print("\n📋 選擇操作:")
        print("1. 單一位置分析")
        print("2. 振動分析")
        print("3. 批次分析")
        print("4. 退出")
        
        choice = input("\n請輸入選項 (1-4): ").strip()
        
        if choice == "1":
            # 單一位置分析
            try:
                x_dist = float(input("X距離 (預設=0): ") or "0")
                y_dist = float(input("Y距離 (預設=-31): ") or "-31")
                offset = float(input("旋轉偏移角度 (預設=10): ") or "10")
                sample_rate = int(input("分析取樣率 (預設=5): ") or "5")
                
                result = engine.analyze_gear_position(
                    x_distance=x_dist,
                    y_distance=y_dist,
                    manual_offset_deg=offset,
                    sample_rate=sample_rate
                )
                
                print(f"\n📊 分析結果:")
                print(f"嚴重程度分數: {result['severity_score']:.2f}")
                print(f"中心距離: {result['transform_info']['center_distance']:.2f} mm")
                
            except ValueError:
                print("❌ 請輸入有效的數值")
            except Exception as e:
                print(f"❌ 分析失敗: {e}")
        
        elif choice == "2":
            # 振動分析
            if engine.current_analysis is None:
                print("⚠️ 請先執行位置分析")
                continue
            
            try:
                rpm_p = int(input("小齒輪轉速 (預設=1800): ") or "1800")
                rpm_g = int(input("大齒輪轉速 (預設=1800): ") or "1800")
                
                vibration_data = engine.simulate_vibration(
                    rpm_pinion=rpm_p,
                    rpm_gear=rpm_g
                )
                
                print(f"\n📊 振動分析完成")
                print(f"嚴重程度分數: {vibration_data['severity_score']:.2f}")
                
            except ValueError:
                print("❌ 請輸入有效的數值")
            except Exception as e:
                print(f"❌ 振動分析失敗: {e}")
        
        elif choice == "3":
            # 批次分析
            try:
                print("輸入分析範圍:")
                x_min = float(input("X最小值 (預設=-20): ") or "-20")
                x_max = float(input("X最大值 (預設=20): ") or "20")
                y_min = float(input("Y最小值 (預設=-40): ") or "-40")
                y_max = float(input("Y最大值 (預設=-20): ") or "-20")
                step = float(input("步長 (預設=5): ") or "5")
                
                results = engine.batch_analysis(
                    x_range=(x_min, x_max),
                    y_range=(y_min, y_max),
                    step=step
                )
                
                print(f"\n📊 批次分析完成，共分析 {len(results)} 個位置")
                
            except ValueError:
                print("❌ 請輸入有效的數值")
            except Exception as e:
                print(f"❌ 批次分析失敗: {e}")
        
        elif choice == "4":
            print("👋 感謝使用齒輪分析系統！")
            break
        
        else:
            print("❌ 無效選項，請重新選擇")

def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(description="齒輪分析系統")
    parser.add_argument("--mode", choices=["interactive", "single", "batch"], 
                       default="interactive", help="運行模式")
    parser.add_argument("--x", type=float, default=0, help="X距離")
    parser.add_argument("--y", type=float, default=-31, help="Y距離")
    parser.add_argument("--offset", type=float, default=10.0, help="旋轉偏移角度")
    parser.add_argument("--sample-rate", type=int, default=5, help="分析取樣率")
    parser.add_argument("--vibration", action="store_true", help="執行振動分析")
    parser.add_argument("--rpm-pinion", type=int, default=1800, help="小齒輪轉速")
    parser.add_argument("--rpm-gear", type=int, default=1800, help="大齒輪轉速")
    parser.add_argument("--batch-x-range", nargs=2, type=float, default=[-20, 20], 
                       help="批次分析X範圍")
    parser.add_argument("--batch-y-range", nargs=2, type=float, default=[-40, -20], 
                       help="批次分析Y範圍")
    parser.add_argument("--batch-step", type=float, default=5, help="批次分析步長")
    parser.add_argument("--no-plots", action="store_true", help="不顯示圖表")
    parser.add_argument("--save-plots", action="store_true", help="保存圖表")
    
    args = parser.parse_args()
    
    if args.mode == "interactive":
        interactive_mode()
    elif args.mode == "single":
        # 單一分析模式
        engine = GearAnalysisEngine()
        engine.initialize()
        
        result = engine.analyze_gear_position(
            x_distance=args.x,
            y_distance=args.y,
            manual_offset_deg=args.offset,
            sample_rate=args.sample_rate,
            show_plots=not args.no_plots,
            save_plots=args.save_plots
        )
        
        if args.vibration:
            engine.simulate_vibration(
                rpm_pinion=args.rpm_pinion,
                rpm_gear=args.rpm_gear,
                show_plots=not args.no_plots,
                save_plots=args.save_plots
            )
    
    elif args.mode == "batch":
        # 批次分析模式
        engine = GearAnalysisEngine()
        engine.initialize()
        
        results = engine.batch_analysis(
            x_range=args.batch_x_range,
            y_range=args.batch_y_range,
            step=args.batch_step
        )

if __name__ == "__main__":
    main()

    """
    使用範例:

    1. 互動模式:
        python main.py --mode interactive

    2. 單一位置分析:
        python main.py --mode single --x 0 --y -31 --offset 10 --sample-rate 5

    3. 單一位置分析並執行振動分析:
        python main.py --mode single --x 0 --y -31 --offset 10 --sample-rate 5 --vibration --rpm-pinion 1800 --rpm-gear 1800

    4. 批次分析:
        python main.py --mode batch --batch-x-range -20 20 --batch-y-range -40 -20 --batch-step 5
    """
"""
增強版齒輪干涉分析模組
使用多維度幾何分析提升精確度
"""
import numpy as np
import trimesh
from typing import Dict, List, Tuple, Any
from config_manager import ConfigManager
from scipy.spatial.distance import cdist

class GearInterferenceAnalyzer:
    def __init__(self):
        """
        初始化干涉分析器
        """
        self.config = ConfigManager()
        # 從配置文件讀取分析參數
        analysis_params = self.config.get_analysis_params()
        
        # 讀取干涉閾值
        thresholds = analysis_params.get('interference_thresholds', {})
        self.distance_threshold_mild = thresholds.get('mild_interference', 0.75)  # mm
        self.distance_threshold_medium = thresholds.get('medium_interference', 1.5)  # mm  
        self.distance_threshold_severe = thresholds.get('severe_interference', 3.0)  # mm
        self.contact_threshold = thresholds.get('contact_threshold', 3.0)  # mm
        self.near_contact_threshold = thresholds.get('near_contact_threshold', 7.5)  # mm
        
        # 其他分析參數
        self.smart_sampling_enabled = analysis_params.get('smart_sampling_enabled', True)
        self.volume_analysis_enabled = analysis_params.get('volume_analysis_enabled', True)
        self.directional_analysis_enabled = analysis_params.get('directional_analysis_enabled', True)
        
        self.interference_data = {}
        self.analysis_results = {}
        
        print(f"干涉分析器初始化完成")
        print(f"  輕微干涉閾值: {self.distance_threshold_mild} mm (重疊深度)")
        print(f"  中度干涉閾值: {self.distance_threshold_medium} mm (重疊深度)")
        print(f"  嚴重干涉閾值: {self.distance_threshold_severe} mm (重疊深度)")
        print(f"  接觸閾值: {self.contact_threshold} mm (間隙)")
        print(f"  接近接觸閾值: {self.near_contact_threshold} mm (間隙)")

        
    def analyze_interference(self, pinion_vertices, pinion_faces, 
                           gear_vertices, gear_faces, sample_rate=5):
        """
        分析齒輪干涉情況 - 改進版本
        
        Args:
            pinion_vertices: 小齒輪頂點
            pinion_faces: 小齒輪面
            gear_vertices: 大齒輪頂點
            gear_faces: 大齒輪面
            sample_rate: 取樣率
            
        Returns:
            dict: 干涉分析結果
        """
        print(f"=== 齒輪重疊分析 (改進版，樣本率: {sample_rate}) ===")
        
        # 重建齒輪mesh物件
        mesh_pinion = trimesh.Trimesh(vertices=pinion_vertices, faces=pinion_faces)
        mesh_gear = trimesh.Trimesh(vertices=gear_vertices, faces=gear_faces)
        
        print(f"小齒輪頂點數: {len(pinion_vertices)}")
        print(f"大齒輪頂點數: {len(gear_vertices)}")
        
        # 計算中心距離
        center_p = np.mean(pinion_vertices, axis=0)
        center_g = np.mean(gear_vertices, axis=0)
        center_distance = np.linalg.norm(center_p - center_g)
        
        print(f"齒輪中心距離: {center_distance:.2f} mm")
        
        # 使用更智能的取樣策略
        vp_sample = self._smart_sampling(pinion_vertices, sample_rate)
        vg_sample = self._smart_sampling(gear_vertices, sample_rate)
        
        print(f"分析樣本點數 - 小齒輪: {len(vp_sample)}, 大齒輪: {len(vg_sample)}")
        
        # 改進的干涉檢測演算法
        interference_data = self._advanced_interference_detection(
            mesh_pinion, mesh_gear, vp_sample, vg_sample, center_p, center_g
        )
        
        # 改進的干涉檢測演算法
        interference_data = self._advanced_interference_detection(
            mesh_pinion, mesh_gear, vp_sample, vg_sample, center_p, center_g
        )
        
        # 計算統計資料
        statistics = self._calculate_enhanced_statistics(interference_data)
        
        # 計算干涉體積和面積（改進版）
        volume_area_data = self._calculate_enhanced_volume_area(
            interference_data, mesh_pinion, mesh_gear
        )
        
        # 計算干涉嚴重程度
        severity_data = self._calculate_interference_severity(
            interference_data, volume_area_data
        )
        
        # 整合分析結果
        self.analysis_results = {
            'center_distance': center_distance,
            'center_p': center_p,
            'center_g': center_g,
            'has_interference': statistics['total_interference_points'] > 0,
            'interference_points': interference_data['interference_points'],
            'statistics': statistics,
            'volume_area': volume_area_data,
            'severity': severity_data,
            'thresholds': interference_data['thresholds'],
            'interference_metrics': interference_data['metrics'],
            'analysis_method': 'enhanced_geometric_analysis'
        }
        
        self._print_analysis_results()
        
        return self.analysis_results
    
    def _smart_sampling(self, vertices, sample_rate):
        """
        智能取樣策略 - 重點採樣齒輪表面和邊緣
        """
        n_vertices = len(vertices)
        
        if sample_rate >= n_vertices:
            return vertices
        
        # 計算每個頂點到中心的距離
        center = np.mean(vertices, axis=0)
        distances_to_center = np.linalg.norm(vertices - center, axis=1)
        
        # 選擇外圍點（齒輪輪廓）和內部關鍵點
        outer_threshold = np.percentile(distances_to_center, 75)
        outer_mask = distances_to_center > outer_threshold
        
        # 外圍點採樣密度更高
        n_outer = min(int(n_vertices / sample_rate * 0.7), np.sum(outer_mask))
        n_inner = int(n_vertices / sample_rate) - n_outer
        
        # 選擇外圍點
        outer_indices = np.where(outer_mask)[0]
        if len(outer_indices) > n_outer:
            outer_selected = np.random.choice(outer_indices, n_outer, replace=False)
        else:
            outer_selected = outer_indices
        
        # 選擇內部點
        inner_indices = np.where(~outer_mask)[0]
        if len(inner_indices) > n_inner and n_inner > 0:
            inner_selected = np.random.choice(inner_indices, n_inner, replace=False)
        else:
            inner_selected = inner_indices[:n_inner] if n_inner > 0 else []
        
        # 合併選擇的點
        selected_indices = np.concatenate([outer_selected, inner_selected])
        return vertices[selected_indices]
    
    def _advanced_interference_detection(self, mesh_pinion, mesh_gear, 
                                       vp_sample, vg_sample, center_p, center_g):
        """
        改進的干涉檢測演算法 - 加入大範圍重疊檢測
        """
        # 使用配置文件中的干涉閾值
        thresholds = {
            'severe_interference': self.distance_threshold_severe,     # 嚴重干涉 - 齒輪明顯重疊
            'medium_interference': self.distance_threshold_medium,     # 中度干涉 - 齒輪輕微重疊  
            'mild_interference': self.distance_threshold_mild,         # 輕微干涉 - 齒輪開始接觸
            'contact_threshold': self.contact_threshold,               # 接觸區域 - 非常接近
            'near_contact_threshold': self.near_contact_threshold      # 接近接觸區域
        }
        
        # === 新增：大範圍重疊預檢測 ===
        large_overlap_detected = self._detect_large_overlap(mesh_pinion, mesh_gear, center_p, center_g)
        
        # 方法1: 基於點到面距離的檢測 (修正版)
        # 使用 trimesh 的 closest_point 來獲得真正的距離（可以是負數）
        try:
            # 計算小齒輪點到大齒輪表面的符號距離
            closest_g, distances_p_to_g, _ = mesh_gear.nearest.on_surface(vp_sample)
            # 檢查點是否在內部（重疊）
            inside_g = mesh_gear.contains(vp_sample)
            min_dist_p_to_g = distances_p_to_g.copy()
            min_dist_p_to_g[inside_g] = -min_dist_p_to_g[inside_g]  # 內部點為負距離
            
            # 計算大齒輪點到小齒輪表面的符號距離  
            closest_p, distances_g_to_p, _ = mesh_pinion.nearest.on_surface(vg_sample)
            inside_p = mesh_pinion.contains(vg_sample)
            min_dist_g_to_p = distances_g_to_p.copy()
            min_dist_g_to_p[inside_p] = -min_dist_g_to_p[inside_p]  # 內部點為負距離
            
            print(f"✅ 使用點到面距離檢測（支援負距離）")
            
            # 如果檢測到大範圍重疊，強制設定負距離
            if large_overlap_detected['major_overlap']:
                print(f"⚠️ 檢測到大範圍重疊，調整距離計算")
                # 對於大範圍重疊，將更多點設為負距離
                overlap_factor = large_overlap_detected['overlap_ratio']
                force_negative_threshold = 1.0 * overlap_factor  # 根據重疊比例調整
                
                min_dist_p_to_g = np.where(min_dist_p_to_g < force_negative_threshold, 
                                          -np.abs(min_dist_p_to_g) - overlap_factor, 
                                          min_dist_p_to_g)
                min_dist_g_to_p = np.where(min_dist_g_to_p < force_negative_threshold,
                                          -np.abs(min_dist_g_to_p) - overlap_factor,
                                          min_dist_g_to_p)
            
        except Exception as e:
            print(f"⚠️ 點到面距離計算失敗，使用備用方法: {e}")
            # 備用方法：點到點距離（只能檢測接近，不能檢測重疊）
            distances_p_to_g = cdist(vp_sample, vg_sample)
            distances_g_to_p = cdist(vg_sample, vp_sample)
            
            min_dist_p_to_g = np.min(distances_p_to_g, axis=1)
            min_dist_g_to_p = np.min(distances_g_to_p, axis=1)
            
            # 對於點到點距離，所有值都是正數，我們需要調整邏輯
            # 將非常小的距離當作重疊來處理
            overlap_threshold = 0.1  # 0.1mm以下當作重疊
            
            # 如果檢測到大範圍重疊，使用更積極的負距離設定
            if large_overlap_detected['major_overlap']:
                overlap_threshold = 2.0 * large_overlap_detected['overlap_ratio']
                print(f"🔧 大範圍重疊調整：重疊閾值 = {overlap_threshold:.2f}mm")
            
            min_dist_p_to_g = np.where(min_dist_p_to_g < overlap_threshold, 
                                     -min_dist_p_to_g - large_overlap_detected['overlap_ratio'], 
                                     min_dist_p_to_g)
            min_dist_g_to_p = np.where(min_dist_g_to_p < overlap_threshold,
                                     -min_dist_g_to_p - large_overlap_detected['overlap_ratio'],
                                     min_dist_g_to_p)
        
        # 方法2: 體積重疊檢測（使用包圍盒）
        overlap_data = self._calculate_volume_overlap(mesh_pinion, mesh_gear)
        
        # 方法3: 基於法向量的方向性檢測
        directional_data = self._calculate_directional_interference(
            vp_sample, vg_sample, center_p, center_g
        )
        
        # 分類干涉點（改進版）
        interference_points = self._classify_interference_points_v2(
            vp_sample, vg_sample, min_dist_p_to_g, min_dist_g_to_p, 
            thresholds, directional_data
        )
        
        # 計算干涉度量
        metrics = {
            'avg_min_distance': (np.mean(min_dist_p_to_g) + np.mean(min_dist_g_to_p)) / 2,
            'min_distance_overall': min(np.min(min_dist_p_to_g), np.min(min_dist_g_to_p)),
            'overlap_volume': overlap_data['volume'],
            'overlap_ratio': overlap_data['ratio'],
            'directional_score': directional_data['interference_score'],
            'large_overlap': large_overlap_detected  # 新增大範圍重疊資訊
        }
        
        return {
            'interference_points': interference_points,
            'thresholds': thresholds,
            'metrics': metrics
        }
    
    def _calculate_volume_overlap(self, mesh_pinion, mesh_gear):
        """
        計算體積重疊
        """
        try:
            # 計算包圍盒
            bbox_p = mesh_pinion.bounds
            bbox_g = mesh_gear.bounds
            
            # 計算重疊區域
            overlap_min = np.maximum(bbox_p[0], bbox_g[0])
            overlap_max = np.minimum(bbox_p[1], bbox_g[1])
            
            # 檢查是否有重疊
            if np.any(overlap_min >= overlap_max):
                return {'volume': 0.0, 'ratio': 0.0}
            
            # 計算重疊體積
            overlap_size = overlap_max - overlap_min
            overlap_volume = np.prod(overlap_size)
            
            # 計算重疊比例
            vol_p = mesh_pinion.volume if hasattr(mesh_pinion, 'volume') else 0
            vol_g = mesh_gear.volume if hasattr(mesh_gear, 'volume') else 0
            total_volume = vol_p + vol_g
            
            overlap_ratio = overlap_volume / total_volume if total_volume > 0 else 0
            
            return {'volume': overlap_volume, 'ratio': overlap_ratio}
            
        except Exception:
            return {'volume': 0.0, 'ratio': 0.0}
    
    def _calculate_directional_interference(self, vp_sample, vg_sample, center_p, center_g):
        """
        基於方向性的干涉檢測
        """
        # 計算從各自中心指向樣本點的方向向量
        directions_p = vp_sample - center_p
        directions_g = vg_sample - center_g
        
        # 正規化方向向量
        norms_p = np.linalg.norm(directions_p, axis=1, keepdims=True)
        norms_g = np.linalg.norm(directions_g, axis=1, keepdims=True)
        
        directions_p_norm = directions_p / (norms_p + 1e-8)
        directions_g_norm = directions_g / (norms_g + 1e-8)
        
        # 計算齒輪間的方向向量
        gear_direction = center_g - center_p
        gear_direction_norm = gear_direction / (np.linalg.norm(gear_direction) + 1e-8)
        
        # 計算方向性干涉分數
        # 如果點在朝向對方齒輪的方向上，則更可能產生干涉
        p_alignment = np.dot(directions_p_norm, gear_direction_norm)
        g_alignment = np.dot(directions_g_norm, -gear_direction_norm)
        
        interference_score = np.mean(np.maximum(p_alignment, 0)) + np.mean(np.maximum(g_alignment, 0))
        
        return {
            'p_alignment': p_alignment,
            'g_alignment': g_alignment,
            'interference_score': interference_score
        }
    
    def _classify_interference_points_v2(self, vp_sample, vg_sample, 
                                        min_dist_p_to_g, min_dist_g_to_p, 
                                        thresholds, directional_data):
        """
        改進的干涉點分類
        """
        interference_points = {}
        
        # 考慮方向性因素的權重
        p_weights = np.maximum(directional_data['p_alignment'], 0)
        g_weights = np.maximum(directional_data['g_alignment'], 0)
        
        # 調整距離閾值（朝向對方的點使用更嚴格的閾值）
        adjusted_dist_p = min_dist_p_to_g * (1 + p_weights)
        adjusted_dist_g = min_dist_g_to_p * (1 + g_weights)
        
        # 重新排序閾值（從最嚴重到最輕微）
        # 負數表示重疊，越負越嚴重
        severe_threshold = -thresholds['severe_interference']      # -5.0mm (最嚴重重疊)
        medium_threshold = -thresholds['medium_interference']      # -3.0mm 
        mild_threshold = -thresholds['mild_interference']          # -1.5mm
        contact_threshold = thresholds['contact_threshold']        # +0.8mm (接觸/小間隙)
        near_contact_threshold = thresholds['near_contact_threshold'] # +1.5mm (接近)
        
        # 嚴重干涉：重疊深度 > 5.0mm (距離 < -5.0)
        severe_mask_p = adjusted_dist_p < severe_threshold
        severe_mask_g = adjusted_dist_g < severe_threshold
        interference_points['severe_p'] = vp_sample[severe_mask_p]
        interference_points['severe_g'] = vg_sample[severe_mask_g]
        
        # 中度干涉：重疊深度 3.0-5.0mm (距離 -5.0 到 -3.0)
        medium_mask_p = ((adjusted_dist_p >= severe_threshold) & 
                        (adjusted_dist_p < medium_threshold))
        medium_mask_g = ((adjusted_dist_g >= severe_threshold) & 
                        (adjusted_dist_g < medium_threshold))
        interference_points['medium_p'] = vp_sample[medium_mask_p]
        interference_points['medium_g'] = vg_sample[medium_mask_g]
        
        # 輕微干涉：重疊深度 1.5-3.0mm (距離 -3.0 到 -1.5)
        mild_mask_p = ((adjusted_dist_p >= medium_threshold) & 
                      (adjusted_dist_p < mild_threshold))
        mild_mask_g = ((adjusted_dist_g >= medium_threshold) & 
                      (adjusted_dist_g < mild_threshold))
        interference_points['mild_p'] = vp_sample[mild_mask_p]
        interference_points['mild_g'] = vg_sample[mild_mask_g]
        
        # 接觸區：輕微重疊到小間隙 (距離 -1.5 到 +0.8)
        contact_mask_p = ((adjusted_dist_p >= mild_threshold) & 
                         (adjusted_dist_p < contact_threshold))
        contact_mask_g = ((adjusted_dist_g >= mild_threshold) & 
                         (adjusted_dist_g < contact_threshold))
        interference_points['contact_p'] = vp_sample[contact_mask_p]
        interference_points['contact_g'] = vg_sample[contact_mask_g]
        
        # 接近接觸：小間隙範圍 (距離 0.8 到 1.5)
        near_mask_p = ((adjusted_dist_p >= contact_threshold) & 
                      (adjusted_dist_p < near_contact_threshold))
        near_mask_g = ((adjusted_dist_g >= contact_threshold) & 
                      (adjusted_dist_g < near_contact_threshold))
        interference_points['near_p'] = vp_sample[near_mask_p]
        interference_points['near_g'] = vg_sample[near_mask_g]
        
        return interference_points
    
    def _detect_large_overlap(self, mesh_pinion, mesh_gear, center_p, center_g):
        """
        檢測大範圍重疊 - 專門處理整體性干涉
        """
        # 計算基本幾何資訊
        center_distance = np.linalg.norm(center_p - center_g)
        
        # 計算齒輪近似半徑
        vertices_p = mesh_pinion.vertices
        vertices_g = mesh_gear.vertices
        
        radius_p = np.max(np.linalg.norm(vertices_p - center_p, axis=1))
        radius_g = np.max(np.linalg.norm(vertices_g - center_g, axis=1))
        
        # 快速幾何檢測
        major_overlap = False
        overlap_ratio = 0
        overlap_severity = "normal"
        
        # 檢測準則
        if center_distance < abs(radius_p - radius_g) * 0.8:
            # 一個齒輪大部分在另一個內部
            major_overlap = True
            overlap_ratio = 0.8
            overlap_severity = "critical_enclosure"
            
        elif center_distance < (radius_p + radius_g) * 0.4:
            # 嚴重重疊
            major_overlap = True
            overlap_ratio = 0.6
            overlap_severity = "severe_overlap"
            
        elif center_distance < (radius_p + radius_g) * 0.7:
            # 中度重疊
            major_overlap = True
            overlap_ratio = 0.4
            overlap_severity = "medium_overlap"
            
        elif center_distance < (radius_p + radius_g) * 0.9:
            # 輕微重疊
            overlap_ratio = 0.2
            overlap_severity = "mild_overlap"
        
        # 包圍盒檢測
        bbox_p = mesh_pinion.bounds
        bbox_g = mesh_gear.bounds
        
        # 計算包圍盒重疊
        overlap_min = np.maximum(bbox_p[0], bbox_g[0])
        overlap_max = np.minimum(bbox_p[1], bbox_g[1])
        
        has_bbox_overlap = np.all(overlap_min < overlap_max)
        bbox_overlap_ratio = 0
        
        if has_bbox_overlap:
            overlap_volume = np.prod(overlap_max - overlap_min)
            volume_p = np.prod(bbox_p[1] - bbox_p[0])
            volume_g = np.prod(bbox_g[1] - bbox_g[0])
            bbox_overlap_ratio = overlap_volume / min(volume_p, volume_g)
            
            # 如果包圍盒重疊很大，也視為主要重疊
            if bbox_overlap_ratio > 0.5:
                major_overlap = True
                overlap_ratio = max(overlap_ratio, bbox_overlap_ratio)
        
        if major_overlap:
            print(f"🚨 檢測到大範圍重疊:")
            print(f"   中心距離: {center_distance:.2f}mm")
            print(f"   半徑和: {radius_p + radius_g:.2f}mm")
            print(f"   重疊程度: {overlap_severity}")
            print(f"   重疊比例: {overlap_ratio:.2f}")
            print(f"   包圍盒重疊: {bbox_overlap_ratio:.3f}")
        
        return {
            'major_overlap': major_overlap,
            'overlap_ratio': overlap_ratio,
            'overlap_severity': overlap_severity,
            'center_distance': center_distance,
            'radius_sum': radius_p + radius_g,
            'bbox_overlap_ratio': bbox_overlap_ratio
        }
    
    def _classify_interference_points(self, vp_sample, vg_sample, 
                                    min_dist_p_to_g, min_dist_g_to_p, thresholds):
        """
        分類干涉點
        """
        interference_points = {}
        
        # 嚴重干涉
        interference_points['severe_p'] = vp_sample[min_dist_p_to_g < thresholds['severe_interference']]
        interference_points['severe_g'] = vg_sample[min_dist_g_to_p < thresholds['severe_interference']]
        
        # 中度干涉
        mask_medium_p = ((min_dist_p_to_g >= thresholds['severe_interference']) & 
                        (min_dist_p_to_g < thresholds['medium_interference']))
        mask_medium_g = ((min_dist_g_to_p >= thresholds['severe_interference']) & 
                        (min_dist_g_to_p < thresholds['medium_interference']))
        interference_points['medium_p'] = vp_sample[mask_medium_p]
        interference_points['medium_g'] = vg_sample[mask_medium_g]
        
        # 輕微干涉
        mask_mild_p = ((min_dist_p_to_g >= thresholds['medium_interference']) & 
                      (min_dist_p_to_g < thresholds['mild_interference']))
        mask_mild_g = ((min_dist_g_to_p >= thresholds['medium_interference']) & 
                      (min_dist_g_to_p < thresholds['mild_interference']))
        interference_points['mild_p'] = vp_sample[mask_mild_p]
        interference_points['mild_g'] = vg_sample[mask_mild_g]
        
        # 接觸區
        mask_contact_p = ((min_dist_p_to_g >= thresholds['mild_interference']) & 
                         (min_dist_p_to_g < thresholds['contact_threshold']))
        mask_contact_g = ((min_dist_g_to_p >= thresholds['mild_interference']) & 
                         (min_dist_g_to_p < thresholds['contact_threshold']))
        interference_points['contact_p'] = vp_sample[mask_contact_p]
        interference_points['contact_g'] = vg_sample[mask_contact_g]
        
        # 接近接觸
        mask_near_p = ((min_dist_p_to_g >= thresholds['contact_threshold']) & 
                      (min_dist_p_to_g < thresholds['near_contact_threshold']))
        mask_near_g = ((min_dist_g_to_p >= thresholds['contact_threshold']) & 
                      (min_dist_g_to_p < thresholds['near_contact_threshold']))
        interference_points['near_p'] = vp_sample[mask_near_p]
        interference_points['near_g'] = vg_sample[mask_near_g]
        
        return interference_points
    
    def _calculate_enhanced_statistics(self, interference_data):
        """
        計算改進的統計資料
        """
        interference_points = interference_data['interference_points']
        metrics = interference_data['metrics']
        
        statistics = {}
        
        # 計算各等級的點數
        for key, points in interference_points.items():
            statistics[f'{key}_count'] = len(points)
        
        # 計算總干涉點數
        total_interference = (len(interference_points['severe_p']) + 
                            len(interference_points['severe_g']) +
                            len(interference_points['medium_p']) + 
                            len(interference_points['medium_g']) +
                            len(interference_points['mild_p']) + 
                            len(interference_points['mild_g']))
        
        statistics['total_interference_points'] = total_interference
        
        # 計算接觸點數
        total_contact = (len(interference_points['contact_p']) + 
                        len(interference_points['contact_g']))
        statistics['total_contact_points'] = total_contact
        
        # 新增干涉度量
        statistics['avg_min_distance'] = metrics['avg_min_distance']
        statistics['min_distance_overall'] = metrics['min_distance_overall']
        statistics['overlap_volume'] = metrics['overlap_volume']
        statistics['overlap_ratio'] = metrics['overlap_ratio']
        statistics['directional_score'] = metrics['directional_score']
        
        return statistics
    
    def _calculate_enhanced_volume_area(self, interference_data, mesh_pinion, mesh_gear):
        """
        計算改進的干涉體積和面積
        """
        interference_points = interference_data['interference_points']
        metrics = interference_data['metrics']
        
        volume_area_data = {}
        
        try:
            # 收集所有干涉點
            all_interference = []
            for key in ['severe_p', 'severe_g', 'medium_p', 'medium_g', 'mild_p', 'mild_g']:
                if len(interference_points[key]) > 0:
                    all_interference.append(interference_points[key])
            
            if all_interference:
                all_interference_points = np.vstack(all_interference)
                
                if len(all_interference_points) >= 4:
                    from scipy.spatial import ConvexHull
                    hull = ConvexHull(all_interference_points)
                    volume_area_data['interference_volume'] = hull.volume
                    volume_area_data['interference_area'] = hull.area
                else:
                    volume_area_data['interference_volume'] = metrics['overlap_volume']
                    volume_area_data['interference_area'] = 0
                
                # 計算干涉區域的邊界框體積
                min_coords = np.min(all_interference_points, axis=0)
                max_coords = np.max(all_interference_points, axis=0)
                bbox_volume = np.prod(max_coords - min_coords)
                volume_area_data['bbox_volume'] = bbox_volume
                
                # 計算干涉密度
                if bbox_volume > 0:
                    volume_area_data['interference_density'] = len(all_interference_points) / bbox_volume
                else:
                    volume_area_data['interference_density'] = 0
            else:
                volume_area_data['interference_volume'] = 0
                volume_area_data['interference_area'] = 0
                volume_area_data['bbox_volume'] = 0
                volume_area_data['interference_density'] = 0
            
            # 添加重疊體積資訊
            volume_area_data['overlap_volume'] = metrics['overlap_volume']
            volume_area_data['overlap_ratio'] = metrics['overlap_ratio']
                
        except Exception as e:
            print(f"計算體積面積時發生錯誤: {e}")
            volume_area_data = {
                'interference_volume': 0,
                'interference_area': 0,
                'bbox_volume': 0,
                'interference_density': 0,
                'overlap_volume': 0,
                'overlap_ratio': 0
            }
        
        return volume_area_data
    
    def _calculate_volume_area(self, interference_points, mesh_pinion, mesh_gear):
        """
        計算干涉體積和面積（近似值）
        """
        volume_area_data = {}
        
        try:
            # 計算重疊區域的近似體積
            all_interference = np.vstack([
                interference_points['severe_p'], interference_points['severe_g'],
                interference_points['medium_p'], interference_points['medium_g'],
                interference_points['mild_p'], interference_points['mild_g']
            ]) if any(len(interference_points[key]) > 0 for key in 
                     ['severe_p', 'severe_g', 'medium_p', 'medium_g', 'mild_p', 'mild_g']) else np.empty((0,3))
            
            if len(all_interference) > 0:
                # 估算干涉區域體積（使用凸包）
                if len(all_interference) >= 4:  # 凸包需要至少4個點
                    from scipy.spatial import ConvexHull
                    hull = ConvexHull(all_interference)
                    volume_area_data['interference_volume'] = hull.volume
                    volume_area_data['interference_area'] = hull.area
                else:
                    volume_area_data['interference_volume'] = 0
                    volume_area_data['interference_area'] = 0
                
                # 計算干涉區域的邊界框體積
                min_coords = np.min(all_interference, axis=0)
                max_coords = np.max(all_interference, axis=0)
                bbox_volume = np.prod(max_coords - min_coords)
                volume_area_data['bbox_volume'] = bbox_volume
            else:
                volume_area_data['interference_volume'] = 0
                volume_area_data['interference_area'] = 0
                volume_area_data['bbox_volume'] = 0
                
        except Exception as e:
            print(f"計算體積面積時發生錯誤: {e}")
            volume_area_data['interference_volume'] = 0
            volume_area_data['interference_area'] = 0
            volume_area_data['bbox_volume'] = 0
        
        return volume_area_data
    
    def _print_analysis_results(self):
        """
        列印分析結果
        """
        print(f"\n=== 干涉和接觸分析結果 ===")
        stats = self.analysis_results['statistics']
        thresholds = self.analysis_results['thresholds']
        
        print(f"嚴重干涉 (重疊>{thresholds['severe_interference']}mm): "
              f"小齒輪 {stats['severe_p_count']}點, 大齒輪 {stats['severe_g_count']}點")
        print(f"中度干涉 (重疊{thresholds['medium_interference']}-{thresholds['severe_interference']}mm): "
              f"小齒輪 {stats['medium_p_count']}點, 大齒輪 {stats['medium_g_count']}點")
        print(f"輕微干涉 (重疊{thresholds['mild_interference']}-{thresholds['medium_interference']}mm): "
              f"小齒輪 {stats['mild_p_count']}點, 大齒輪 {stats['mild_g_count']}點")
        print(f"接觸區 (間隙0-{thresholds['contact_threshold']}mm): "
              f"小齒輪 {stats['contact_p_count']}點, 大齒輪 {stats['contact_g_count']}點")
        print(f"接近接觸 (間隙{thresholds['contact_threshold']}-{thresholds['near_contact_threshold']}mm): "
              f"小齒輪 {stats['near_p_count']}點, 大齒輪 {stats['near_g_count']}點")
        
        print(f"\n總干涉點數: {stats['total_interference_points']}")
        print(f"總接觸點數: {stats['total_contact_points']}")
        
        volume_area = self.analysis_results['volume_area']
        print(f"\n體積面積分析:")
        print(f"干涉區域體積: {volume_area['interference_volume']:.3f} mm³")
        print(f"干涉區域面積: {volume_area['interference_area']:.3f} mm²")
        print(f"邊界框體積: {volume_area['bbox_volume']:.3f} mm³")
    
    def get_interference_severity_score(self):
        """
        計算干涉嚴重程度分數 (0-100)
        
        Returns:
            float: 嚴重程度分數，越高表示干涉越嚴重
        """
        if not self.analysis_results:
            return 0
        
        stats = self.analysis_results['statistics']
        
        # 權重分配：嚴重干涉權重最高
        severe_weight = 10
        medium_weight = 5
        mild_weight = 2
        contact_weight = 1
        
        total_weighted_score = (
            stats['severe_p_count'] * severe_weight +
            stats['severe_g_count'] * severe_weight +
            stats['medium_p_count'] * medium_weight +
            stats['medium_g_count'] * medium_weight +
            stats['mild_p_count'] * mild_weight +
            stats['mild_g_count'] * mild_weight +
            stats['contact_p_count'] * contact_weight +
            stats['contact_g_count'] * contact_weight
        )
        
        # 正規化到0-100
        max_possible_score = 1000  # 假設最大可能分數
        severity_score = min(100, (total_weighted_score / max_possible_score) * 100)
        
        return severity_score
    
    def _calculate_interference_severity(self, interference_data, volume_area_data):
        """
        計算干涉嚴重程度，結合多個因子（優化梯度分布）+ 大範圍重疊檢測
        """
        # 如果interference_data已經包含statistics，直接使用
        if 'statistics' in interference_data:
            statistics = interference_data['statistics']
        else:
            # 否則先計算statistics
            statistics = self._calculate_enhanced_statistics(interference_data)
            
        metrics = interference_data['metrics']
        
        # 基礎嚴重程度計算 (0-100)
        base_score = 0
        
        # === 新增：大範圍重疊檢測加分 ===
        large_overlap_bonus = 0
        if 'large_overlap' in metrics:
            overlap_data = metrics['large_overlap']
            if overlap_data['major_overlap']:
                if overlap_data['overlap_severity'] == 'critical_enclosure':
                    large_overlap_bonus = 40  # 齒輪嵌套
                elif overlap_data['overlap_severity'] == 'severe_overlap':
                    large_overlap_bonus = 30  # 嚴重重疊
                elif overlap_data['overlap_severity'] == 'medium_overlap':
                    large_overlap_bonus = 20  # 中度重疊
                else:
                    large_overlap_bonus = 10  # 輕微重疊
                    
                base_score += large_overlap_bonus
                print(f"🚨 大範圍重疊加分: +{large_overlap_bonus} ({overlap_data['overlap_severity']})")
        
        # 干涉點密度評分 (0-35) - 使用對數標度來避免快速飽和
        total_interference = statistics.get('total_interference_points', 0)
        density_score = 0
        if total_interference > 0:
            # 使用對數標度：log(1 + 干涉點數) * 係數
            density_score = min(35, np.log(1 + total_interference) * 6)
            base_score += density_score
        
        # 嚴重干涉比例評分 (0-30)
        severe_count = (statistics.get('severe_p_count', 0) + 
                       statistics.get('severe_g_count', 0))
        severe_ratio = 0
        if total_interference > 0:
            severe_ratio = severe_count / total_interference
            base_score += severe_ratio * 30
        
        # 體積重疊評分 (0-20)
        overlap_ratio = metrics.get('overlap_ratio', 0)
        base_score += min(20, overlap_ratio * 20)
        
        # 方向性干涉評分 (0-10)
        directional_score = metrics.get('directional_score', 0)
        base_score += directional_score * 10
        
        # 距離因子評分 - 更細緻的距離評估
        min_distance = metrics.get('min_distance_overall', float('inf'))
        distance_bonus = 0
        if min_distance < 5.0:  # 如果有點距離小於5mm
            # 使用反比例函數來計算距離獎勵
            if min_distance > 0:
                distance_bonus = min(15, 15 / (min_distance + 0.1))
            else:
                distance_bonus = 15  # 重疊情況
            base_score += distance_bonus
        
        # 限制在0-100範圍內
        severity_score = max(0, min(100, base_score))
        
        # 重新調整分級閾值，提供更好的梯度
        if severity_score >= 80:
            severity_level = "Critical"
            description = "嚴重碰撞，齒輪大量重疊，需要立即調整"
        elif severity_score >= 60:
            severity_level = "High"
            description = "高度干涉，齒輪明顯接觸，建議調整間隙"
        elif severity_score >= 40:
            severity_level = "Medium"
            description = "中度干涉，齒輪有接觸，可能影響運轉"
        elif severity_score >= 25:
            severity_level = "Low"
            description = "輕微干涉，齒輪接近，建議監控"
        elif severity_score >= 10:
            severity_level = "Minimal"
            description = "極輕微接觸，接近正常範圍"
        else:
            severity_level = "Normal"
            description = "正常間隙，運轉良好"
        
        return {
            'severity_score': severity_score,
            'severity_level': severity_level,
            'description': description,
            'factors': {
                'interference_density': density_score,
                'severe_ratio': severe_ratio * 30,
                'overlap_volume': min(20, overlap_ratio * 20),
                'directional_factor': directional_score * 10,
                'distance_bonus': distance_bonus
            }
        }

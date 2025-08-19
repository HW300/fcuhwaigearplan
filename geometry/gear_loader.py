"""
齒輪載入與環境設置模組
"""
import trimesh
import numpy as np
import math
import os

class GearLoader:
    def __init__(self, stl_path="/Users/rich/Documents/code/gear2D_proj/RL_project/STL_data"):
        """
        初始化齒輪載入器
        
        Args:
            stl_path: STL檔案路徑
        """
        self.stl_path = stl_path
        self.pinion_path = f"{stl_path}/Pinion_1TH00038_v2.0.STL"
        self.gear_path = f"{stl_path}/Gear_1TH00037_v2.0.STL"
        
    def load_stl_files(self):
        """
        載入STL檔案
        
        Returns:
            tuple: (pinion_mesh, gear_mesh)
        """
        try:
            pinion_mesh = trimesh.load_mesh(self.pinion_path)
            gear_mesh = trimesh.load_mesh(self.gear_path)
            print(f"成功載入齒輪檔案:")
            print(f"- 小齒輪: {self.pinion_path}")
            print(f"- 大齒輪: {self.gear_path}")
            return pinion_mesh, gear_mesh
        except Exception as e:
            print(f"載入STL檔案時發生錯誤: {e}")
            return None, None
    
    def find_mounting_face_center(self, mesh, z_face='max', tol=0.5):
        """
        找承靠面圓心與對應面上的點
        
        Args:
            mesh: 網格物件
            z_face: 'max' 或 'min'，選擇最大或最小Z值面
            tol: 容差值
            
        Returns:
            tuple: (center_point, face_points)
        """
        verts = mesh.vertices
        z_val = verts[:, 2].max() if z_face == 'max' else verts[:, 2].min()
        face_pts_idx = np.where(np.abs(verts[:, 2] - z_val) < tol)[0]
        face_pts = verts[face_pts_idx]
        center_xy = face_pts[:, :2].mean(axis=0)
        return np.array([center_xy[0], center_xy[1], z_val]), face_pts
    
    def setup_environment(self):
        """
        設置必要的環境變數和檢查
        """
        try:
            import vtkmodules.vtkCommonDataModel
            print("VTK 匯入成功")
        except ImportError:
            print("警告: VTK 未安裝或匯入失敗")
        
        try:
            import cq_gears.bevel_gear as bg
            print("cq_gears 匯入成功")
            # 列出結尾帶 Gear 的屬性
            gear_classes = [name for name in dir(bg) if name.endswith("Gear")]
            print(f"可用的齒輪類別: {gear_classes}")
        except ImportError:
            print("警告: cq_gears 未安裝或匯入失敗")
        
        return True

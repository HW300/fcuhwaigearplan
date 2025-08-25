"""
齒輪移動與變換模組
"""
import trimesh
import numpy as np
import math
import os
from dotenv import load_dotenv

load_dotenv()
DEBUG=int(os.getenv("DEBUG", 0))


class GearTransformer:
    def __init__(self):
        """
        初始化齒輪變換器
        """
        self.pinion_mesh = None
        self.gear_mesh = None
        self.pinion_original = None
        self.gear_original = None
        
    def setup_gears(self, pinion_mesh, gear_mesh):
        """
        設置齒輪網格物件
        
        Args:
            pinion_mesh: 小齒輪網格
            gear_mesh: 大齒輪網格
        """
        self.pinion_mesh = pinion_mesh.copy()
        self.gear_mesh = gear_mesh.copy()
        self.pinion_original = pinion_mesh.copy()
        self.gear_original = gear_mesh.copy()
    
    def find_mounting_face_center(self, mesh, z_face='max', tol=0.5):
        """
        找承靠面圓心與對應面上的點
        """
        verts = mesh.vertices
        z_val = verts[:, 2].max() if z_face == 'max' else verts[:, 2].min()
        face_pts_idx = np.where(np.abs(verts[:, 2] - z_val) < tol)[0]
        face_pts = verts[face_pts_idx]
        center_xy = face_pts[:, :2].mean(axis=0)
        return np.array([center_xy[0], center_xy[1], z_val]), face_pts
    
    def transform_gears(self, x_distance=24, y_distance=-31, m=2, zp=20, zg=20, 
                       manual_offset_deg=10.0):
        """
        進行齒輪變換和定位
        
        Args:
            x_distance: X方向距離（小齒輪移動方向）
            y_distance: Y方向距離（大齒輪移動方向）
            m: 模數
            zp: 小齒輪齒數
            zg: 大齒輪齒數
            manual_offset_deg: 手動微調角度
            
        Returns:
            tuple: (pinion_vertices, pinion_faces, gear_vertices, gear_faces, transform_info)
        """
        # 找承靠面圓心與點雲
        pinion_center, pinion_face_pts = self.find_mounting_face_center(self.pinion_mesh, z_face='max')
        gear_center, gear_face_pts = self.find_mounting_face_center(self.gear_mesh, z_face='max')
        
        # Step 1：平移至原點
        self.pinion_mesh.apply_translation(-pinion_center)
        self.gear_mesh.apply_translation(-gear_center)
        
        # Step 2：旋轉方向（Pinion→X，Gear→Y）
        self.pinion_mesh.apply_transform(trimesh.transformations.rotation_matrix(-math.pi/2, [0, 1, 0]))
        self.gear_mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2, [1, 0, 0]))
        
        # Step 3：自動對齒旋轉
        theta_contact = math.atan2(y_distance, x_distance)
        tooth_pitch_p = 2 * math.pi / zp
        tooth_pitch_g = 2 * math.pi / zg
        pinion_rotation = theta_contact % tooth_pitch_p
        gear_rotation = theta_contact % tooth_pitch_g
        
        # 計算齒尖初始偏移角
        align_offset = (tooth_pitch_p - tooth_pitch_g) / 2
        manual_offset = math.radians(manual_offset_deg)
        
        # 加入旋轉
        self.gear_mesh.apply_transform(trimesh.transformations.rotation_matrix(align_offset, [0, 0, 1]))
        self.pinion_mesh.apply_transform(trimesh.transformations.rotation_matrix(-pinion_rotation, [0, 1, 0]))
        self.gear_mesh.apply_transform(trimesh.transformations.rotation_matrix(-gear_rotation + manual_offset, [0, 1, 0]))
        
        # Step 4：放置mesh
        pinion_vertices, pinion_faces = self.place_mesh(self.pinion_mesh, np.array([0, 0, 0]))
        gear_vertices, gear_faces = self.place_mesh(self.gear_mesh, np.array([x_distance, y_distance, 0]))
        
        # 計算變換後的中心點和距離
        center_p = np.mean(pinion_vertices, axis=0)
        center_g = np.mean(gear_vertices, axis=0)
        center_distance = np.linalg.norm(center_p - center_g)
        
        transform_info = {
            'pinion_center': center_p,
            'gear_center': center_g,
            'center_distance': center_distance,
            'x_distance': x_distance,
            'y_distance': y_distance,
            'manual_offset_deg': manual_offset_deg,
            'tooth_pitch_p': tooth_pitch_p,
            'tooth_pitch_g': tooth_pitch_g
        }
        
        return pinion_vertices, pinion_faces, gear_vertices, gear_faces, transform_info
    
    def place_mesh(self, mesh, translate):
        """
        放置網格物件
        
        Args:
            mesh: 網格物件
            translate: 平移向量
            
        Returns:
            tuple: (vertices, faces)
        """
        verts = mesh.vertices + translate
        return verts, mesh.faces
    
    def reset_gears(self):
        """
        重置齒輪到原始狀態
        """
        if self.pinion_original is not None and self.gear_original is not None:
            self.pinion_mesh = self.pinion_original.copy()
            self.gear_mesh = self.gear_original.copy()
            if(DEBUG):
                print("齒輪已重置到原始狀態")
        else:
            print("警告: 沒有原始齒輪資料可以重置")

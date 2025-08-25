"""
配置管理模組
用於統一管理所有可調整參數
"""
import json
import os

from dotenv import load_dotenv

load_dotenv()
DEBUG=int(os.getenv("DEBUG", 0))
# print(f"[DEBUG] DEBUG value loaded: {DEBUG}")

class ConfigManager:
    def __init__(self, config_path=None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路徑，默認為當前目錄下的config.json
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """載入配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if(DEBUG):
                print(DEBUG)
                print(f"✅ 配置文件載入成功: {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"⚠️ 配置文件不存在: {self.config_path}")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"❌ 配置文件格式錯誤: {e}")
            return self._get_default_config()
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置文件保存成功: {self.config_path}")
        except Exception as e:
            print(f"❌ 配置文件保存失敗: {e}")
    
    def get(self, *keys):
        """
        獲取配置值
        
        Args:
            *keys: 配置鍵路徑，例如 get('gear_parameters', 'pinion', 'teeth')
        
        Returns:
            配置值
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def set(self, *keys, value):
        """
        設置配置值
        
        Args:
            *keys: 配置鍵路徑
            value: 要設置的值
        """
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def _get_default_config(self):
        """獲取默認配置"""
        return {
            "gear_parameters": {
                "pinion": {"teeth": 20, "module": 2.0, "rpm": 1800},
                "gear": {"teeth": 20, "module": 2.0, "rpm": 1800}
            },
            "analysis_parameters": {
                "default_sample_rate": 5,
                "interference_thresholds": {
                    "severe_interference": 2.0,
                    "medium_interference": 1.0,
                    "mild_interference": 0.5,
                    "contact_threshold": 2.0,
                    "near_contact_threshold": 5.0
                }
            },
            "vibration_parameters": {
                "sampling_frequency": 10000,
                "signal_duration": 2.0,
                "harmonics": {
                    "pinion_harmonics": 8,
                    "gear_harmonics": 8,
                    "mesh_harmonics": 6,
                    "sideband_orders": 4
                }
            }
        }
    
    # 便捷方法
    def get_gear_params(self):
        """獲取齒輪參數"""
        return self.get('gear_parameters')
    
    def get_position_params(self):
        """獲取位置參數"""
        return self.get('position_parameters')
    
    def get_analysis_params(self):
        """獲取分析參數"""
        return self.get('analysis_parameters')
    
    def get_vibration_params(self):
        """獲取振動參數"""
        return self.get('vibration_parameters')
    
    def get_visualization_params(self):
        """獲取可視化參數"""
        return self.get('visualization_parameters')
    
    def print_config(self):
        """列印當前配置"""
        print("=" * 50)
        print("當前配置:")
        print("=" * 50)
        print(json.dumps(self.config, indent=2, ensure_ascii=False))
        print("=" * 50)

# 全局配置實例
config_manager = ConfigManager()

def get_config():
    """獲取全局配置管理器"""
    return config_manager

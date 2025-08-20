# 當前配置摘要驗證

import sys
import os
sys.path.append('/Users/rich/Documents/code/gear2D_proj/project')

from config_manager import ConfigManager

config = ConfigManager()
gear_params = config.get_gear_params()

print("🔧 當前齒輪配置參數驗證")
print("=" * 50)
print(f"📁 配置文件路徑: {config.config_path}")
print()
print(f"🔹 小齒輪 (Pinion):")
print(f"   齒數: {gear_params['pinion']['teeth']} 齒")
print(f"   轉速: {gear_params['pinion']['rpm']} RPM")
print(f"   頻率: {gear_params['pinion']['rpm']/60:.1f} Hz")
print()
print(f"🔸 大齒輪 (Gear):")  
print(f"   齒數: {gear_params['gear']['teeth']} 齒")
print(f"   轉速: {gear_params['gear']['rpm']} RPM")
print(f"   頻率: {gear_params['gear']['rpm']/60:.1f} Hz")
print()
print(f"📊 比例關係:")
print(f"   齒數比: {gear_params['gear']['teeth']/gear_params['pinion']['teeth']:.1f}:1")
print(f"   轉速比: {gear_params['pinion']['rpm']/gear_params['gear']['rpm']:.1f}:1")
print(f"   頻率比: {(gear_params['pinion']['rpm']/60)/(gear_params['gear']['rpm']/60):.1f}:1")
print()
print(f"🎯 GMF (嚙合頻率): {(gear_params['pinion']['rpm']/60) * gear_params['pinion']['teeth']:.1f} Hz")
print()

# 驗證齒輪組合的正確性
pinion_teeth = gear_params['pinion']['teeth']
gear_teeth = gear_params['gear']['teeth']
pinion_rpm = gear_params['pinion']['rpm']  
gear_rpm = gear_params['gear']['rpm']

# 檢查齒數比和轉速比是否匹配
teeth_ratio = gear_teeth / pinion_teeth
speed_ratio = pinion_rpm / gear_rpm

if abs(teeth_ratio - speed_ratio) < 0.1:
    print("✅ 齒數比與轉速比匹配正確")
else:
    print("❌ 齒數比與轉速比不匹配")
    
if teeth_ratio >= 2.5:
    print("✅ 齒數比合理 (適合減速傳動)")
else:
    print("⚠️ 齒數比偏小")
    
print("=" * 50)

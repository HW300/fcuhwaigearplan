"""
專案初始化腳本
"""

def check_dependencies():
    """檢查所需依賴套件"""
    required_packages = [
        'trimesh',
        'plotly', 
        'numpy',
        'scipy',
        'ipywidgets',
        'matplotlib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - 已安裝")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - 未安裝")
    
    if missing_packages:
        print(f"\n需要安裝的套件: {', '.join(missing_packages)}")
        print("安裝指令:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    else:
        print("\n✅ 所有依賴套件都已安裝！")
        return True

def check_stl_files():
    """檢查STL檔案是否存在"""
    import os
    
    base_path = "/Users/rich/Documents/code/gear2D_proj/"
    files_to_check = [
        "Pinion_1TH00038_v2.0.STL",
        "Gear_1TH00037_v2.0.STL"
    ]
    
    all_files_exist = True
    
    for filename in files_to_check:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            print(f"✅ {filename} - 檔案存在")
        else:
            print(f"❌ {filename} - 檔案不存在")
            all_files_exist = False
    
    return all_files_exist

def initialize_project():
    """初始化專案"""
    print("=" * 50)
    print("齒輪2D分析專案初始化")
    print("=" * 50)
    
    print("\n📦 檢查依賴套件...")
    deps_ok = check_dependencies()
    
    print("\n📁 檢查STL檔案...")
    files_ok = check_stl_files()
    
    print("\n" + "=" * 50)
    if deps_ok and files_ok:
        print("🎉 專案初始化完成！可以開始使用 main.ipynb")
    else:
        print("⚠️ 初始化未完成，請解決上述問題後重試")
    print("=" * 50)
    
    return deps_ok and files_ok

if __name__ == "__main__":
    initialize_project()

# 測試控制面板功能
# 建立控制面板實例
control_panel = GearControlPanel(transformer, visualizer, analyzer, vibration_sim, vib_data_analyzer)

# 測試梯度分析功能
print("🔍 測試梯度分析功能...")
control_panel.on_gradient_test_click(None)

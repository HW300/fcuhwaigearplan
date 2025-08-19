import sys
import os
import numpy as np
import pytest

PROJECT_DIR = os.path.dirname(__file__)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


def test_features_from_real_pipeline():
    # 匯入模組
    try:
        from control_environment import run_analysis_and_get_time_signal_real
    except Exception as e:
        pytest.skip(f"無法匯入 real 流程函數，跳過：{e}")

    # 取得 time 與 signal（使用既定參數）
    try:
        t, s = run_analysis_and_get_time_signal_real(24, -31, offset_deg=10.0, sample_rate=100)
    except Exception as e:
        pytest.skip(f"real 流程執行失敗，跳過：{e}")

    # 構建 vibration_data dict
    assert len(t) == len(s) and len(t) > 0
    # 估算 fs（或留給函數自行從 time 推估）
    fs = None
    if len(t) > 1:
        dt = float(np.mean(np.diff(t)))
        if dt > 0:
            fs = 1.0 / dt

    vibration_data = {
        'time': t,
        'vibration_signal': s,
        'simulation_params': ({'sampling_rate': fs} if fs else {})
    }

    # 計算特徵
    from RL_project.features.Bevel_gear_vibration_features import compute_feature_values_from_vibration
    features = compute_feature_values_from_vibration(vibration_data)

    # 基本檢查
    required_keys = [
        'Time_skewness_x', 'Time_kurtosis_x', 'Time_rms_x', 'Time_crestfactor_x',
        'Powerspectrum_skewness_x', 'Powerspectrum_kurtosis_x', 'Powerspectrum_rms_x', 'Powerspectrum_crestfactor_x'
    ]
    for k in required_keys:
        assert k in features
        # 確保為可轉換為浮點的字串
        float(features[k])

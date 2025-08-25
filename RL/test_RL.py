from typing import Dict, Tuple, List, Callable
import math
from control_environment import run_analysis_and_get_time_signal as run_analysis
from Control.control_test import *

# x=24
# y=-31
# offset=0
# sample=150

# res=run_analysis(x,  y,  offset, sample)
# print("[DEBUG] feedback result: ", res)


# =========================
# 範例：如何啟動
# =========================
if __name__ == "__main__":
    # TODO: 將此函式換成你的現場實作（移動 + 量測 + 回傳扁平 JSON）
    # def run_analysis(x: float, y: float) -> Dict[str, float]:
    #     """
    #     範例 stub：請改成你的真實 I/O。
    #     回傳的 keys 請符合 REQUIRED_KEYS（見上方）。
    #     """
    #     raise NotImplementedError("請用你的現場 run_analysis(x,y) 實作替換此函式")

    # 限位（單位與你的 run_analysis 相同）

    start_x=14
    start_y=-21
    std_x=24
    std_y=-31

    limits = Limits(
        x_min=std_x-5.50, x_max=std_x+5.50,
        y_min=std_y-5.50, y_max=std_y+5.50
    )

    # 權重 / 安全 / 步長 / 控制參數（可依現場微調）
    # 設定 reward 計算時的各特徵權重
    weights = CVIWeights(
        w_trms=1.0,   # 時域 RMS（主要目標：整體振動大小）
        w_tcf=0.5,    # 時域 Crest Factor（尖峰比，抑制突發衝擊）
        w_frms=0.6,   # 頻譜 RMS（頻域能量）
        w_fsk=0.2,    # 頻譜偏度（分布偏斜）
        w_fkurt=0.3   # 頻譜峰度（異常尖銳能量峰）
    )

    # 設定安全門檻，超過即視為危險
    safety  = SafetyThresholds(
        time_rms_max=5.0,   # 時域 RMS 上限
        time_cf_max=10.0    # Crest Factor 上限
    )

    # 步長控制（等邊三角形的大小）
    steps   = StepConfig(
        sig_x=2,       # 初始 X 步長（單位與 run_analysis 相同）
        sig_y=2,       # 初始 Y 步長
        sig_x_min=0.0005,# X 最小步長（避免縮到 0）
        sig_y_min=0.0005,# Y 最小步長
        sig_x_max=2.5,     # X 最大步長（避免過度搜索）
        sig_y_max=2.5,     # Y 最大步長
        up_scale=1.2,    # 若找到更好點 → 步長放大 20%
        down_scale=0.8   # 若沒改善 → 步長縮小 20%
    )

    # 強化學習控制參數
    cfg     = RLConfig(
        alpha=0.3,           # 位置更新時的低通濾波係數, ie: 新位置 = 舊位置*0.7 + 最佳候選點*0.3
        K=1,                 # 每個候選點量測次數（1 表示只量一次）
        epsilon=1e-3,        # reward 提升超過 0.001 才算真正改善
        lambda_move=0.0,     # 動作代價（0=不懲罰大移動，可設小值避免亂跳）
        max_iters=50,        # 最多迭代 N 回合
        no_improve_patience=10# 連續 5 回合沒有改善就停止
    )

    # 建立最佳化器
    opt = Top1of3WithRunAnalysis(
        run_fn=run_analysis,   # 呼叫你的函式，移動機台並回傳振動特徵 JSON
        start_xy=(start_x, start_y), # 初始位置
        limits=limits,         # 機械範圍限制（x,y 最小與最大值）
        steps=steps,           # 步長控制設定
        cfg=cfg,               # RL 控制參數
        w=weights,             # CVI 權重（決定 reward 計算）
        thr=safety             # 安全門檻（避免危險狀態）
    )


    # Before optimization: Capture initial vibration data
    before_features = run_analysis(start_x, start_y)

    # 開跑
    best_x, best_y, best_r = opt.run()
    print(f"[DEBUG] Finished at ({best_x:.6f}, {best_y:.6f}), best_reward={best_r:.6f}")

    # After optimization: Capture vibration data at the best position
    after_features = run_analysis(best_x, best_y)

    # 畫圖：每次迭代的候選點/路徑/收斂
    try:
        from visualization.rl_visualization import plot_rl_history, plot_vibration_comparison
        plot_rl_history(opt.history, show=True, save_prefix="rl_iter")

        # Compare vibration features
        # 軸向選擇：[x, y, z] 其中 1=顯示, 0=不顯示
        # 例如：[1,1,0] 顯示x和y軸，[1,0,0] 只顯示x軸，[0,0,1] 只顯示z軸
        axes_selection = [1, 0, 0]  # 顯示 X 和 Y 軸
        plot_vibration_comparison(
            before_features, after_features,
            axes_selection=axes_selection,
            show=True, save_path="feature_comparison.png"
        )
    except Exception as e:
        print(f"[DEBUG] ⚠️ 視覺化失敗：{e}")

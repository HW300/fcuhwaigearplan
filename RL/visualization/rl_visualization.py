# -*- coding: utf-8 -*-
"""
RL 迭代結果視覺化工具
- 路徑圖：位置 (x,y) 與候選點，標示 unsafe 與所選
- 收斂圖：best_reward 隨迭代變化
- 步長圖：sigma_x / sigma_y 隨迭代變化
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional


def plot_rl_history(history: List[Dict[str, Any]], show: bool = True, save_prefix: Optional[str] = None):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠️ 無法繪圖：未安裝 matplotlib。可先安裝：pip install matplotlib")
        return False

    if not history:
        print("⚠️ 無歷史資料可供繪圖")
        return False

    # 準備資料
    xs = [h['pos']['x'] for h in history]
    ys = [h['pos']['y'] for h in history]
    br = [h['best_reward'] for h in history]
    sx = [h['sigmas']['x'] for h in history]
    sy = [h['sigmas']['y'] for h in history]

    fig, axes = plt.subplots(1, 3, figsize=(16, 4))

    # 1) 路徑 + 候選點
    ax0 = axes[0]
    ax0.plot(xs, ys, "-o", color="#1f77b4", markersize=3, linewidth=1, label="pos")
    ax0.set_title("XY Path and Candidates")
    ax0.set_xlabel("x")
    ax0.set_ylabel("y")
    # 疊加候選點（每回合）
    for h in history:
        dbg = h.get('debug') or {}
        cands = dbg.get('candidates') or []
        chosen = dbg.get('chosen')
        for c in cands:
            if c.get('unsafe'):
                ax0.plot(c['x'], c['y'], 'x', color='red', markersize=5, alpha=0.8)
            else:
                ax0.plot(c['x'], c['y'], 'o', color='green', markersize=3, alpha=0.6)
        if chosen is not None:
            ax0.plot(chosen['x'], chosen['y'], '*', color='orange', markersize=8, alpha=0.9)
    ax0.grid(True, alpha=0.3)

    # 2) best_reward
    ax1 = axes[1]
    ax1.plot(range(1, len(br)+1), br, "-o", color="#2ca02c", markersize=3)
    ax1.set_title("Best reward Convergence")
    ax1.set_xlabel("iter")
    ax1.set_ylabel("best_reward")
    ax1.grid(True, alpha=0.3)

    # 3) 步長
    ax2 = axes[2]
    ax2.plot(range(1, len(sx)+1), sx, label="sigma_x")
    ax2.plot(range(1, len(sy)+1), sy, label="sigma_y")
    ax2.set_title("Step length (sigma)")
    ax2.set_xlabel("iter")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()

    if save_prefix:
        import os
        out_path = f"{save_prefix}_summary.png"
        fig.savefig(out_path, dpi=150, bbox_inches='tight')
        print(f"💾 已儲存: {out_path}")

    if show:
        plt.show()
    return True


def plot_vibration_comparison(
    before_features: dict[str, float], after_features: dict[str, float],
    axes_selection: list[int] = [1, 0, 0],  # [x, y, z] 1=顯示, 0=不顯示
    show: bool = True, save_path: str | None = None
):
    """
    繪製特徵數據的 before/after 比較圖。
    可選擇要顯示的軸向，每個特徵會個別正規化為 0-1 範圍以便比較。

    Args:
        before_features: 初始位置的特徵數據。
        after_features: 最佳位置的特徵數據。
        axes_selection: [x, y, z] 列表，1=顯示該軸，0=不顯示。例如 [1,1,0] 表示顯示x和y軸
        show: 是否顯示圖表。
        save_path: 若提供，儲存圖檔至指定路徑。
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("⚠️ 無法繪圖：未安裝 matplotlib 或 numpy。可先安裝：pip install matplotlib numpy")
        return False

    # 根據選擇的軸向過濾特徵
    axis_names = ['x', 'y', 'z']
    selected_axes = [axis_names[i] for i, selected in enumerate(axes_selection) if selected == 1]
    
    if not selected_axes:
        print("⚠️ 請至少選擇一個軸向進行比較")
        return False
    
    # 建立要顯示的特徵鍵列表
    selected_keys = []
    for key in before_features.keys():
        for axis in selected_axes:
            if key.endswith(f'_{axis}'):
                selected_keys.append(key)
    
    if not selected_keys:
        print(f"⚠️ 找不到選定軸向 {selected_axes} 的振動特徵數據")
        return False
    
    # 確保鍵一致
    after_selected_keys = [key for key in after_features.keys() 
                          for axis in selected_axes if key.endswith(f'_{axis}')]
    if set(selected_keys) != set(after_selected_keys):
        raise ValueError("Before 和 After 的選定軸向特徵鍵不一致")

    # 準備原始數據
    before_values = [before_features[k] for k in selected_keys]
    after_values = [after_features[k] for k in selected_keys]
    
    # 個別正規化每個特徵到 0-1 範圍
    normalized_before = []
    normalized_after = []
    improvement_ratios = []
    
    for i, key in enumerate(selected_keys):
        before_val = before_values[i]
        after_val = after_values[i]
        
        # 使用較大的值作為基準來正規化（避免都變成0和1的問題）
        max_val = max(abs(before_val), abs(after_val))
        
        # 避免除零錯誤
        if max_val == 0:
            norm_before = 0.5
            norm_after = 0.5
        else:
            # 相對於最大值正規化，保持比例關係
            norm_before = abs(before_val) / max_val
            norm_after = abs(after_val) / max_val
        
        normalized_before.append(norm_before)
        normalized_after.append(norm_after)
        
        # 計算改善比例（負值表示增加，正值表示減少）
        if before_val != 0:
            improvement = (before_val - after_val) / abs(before_val) * 100
        else:
            improvement = 0
        improvement_ratios.append(improvement)

    x = np.arange(len(selected_keys))

    # 創建兩個子圖
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # 第一個子圖：正規化比較
    width = 0.35
    bars1 = ax1.bar(x - width/2, normalized_before, width, label="Before (Normalized)", color="blue", alpha=0.7)
    bars2 = ax1.bar(x + width/2, normalized_after, width, label="After (Normalized)", color="green", alpha=0.7)

    # 動態生成標題
    axes_str = ', '.join([f'{axis.upper()}-axis' for axis in selected_axes])
    ax1.set_title(f"Feature Comparison ({axes_str}) - Normalized to 0-1 Range")
    ax1.set_xlabel(f"Features ({axes_str})")
    ax1.set_ylabel("Normalized Values")
    ax1.set_xticks(x)
    
    # 簡化標籤，移除軸向後綴並加上軸向標識
    simplified_labels = []
    for key in selected_keys:
        # 移除軸向後綴
        base_name = key.rsplit('_', 1)[0]
        axis_suffix = key.rsplit('_', 1)[1]
        simplified_labels.append(f"{base_name}({axis_suffix})")
    
    ax1.set_xticklabels(simplified_labels, rotation=45, ha="right")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1.1)
    
    # 在柱狀圖上標註原始數值
    for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
        ax1.text(bar1.get_x() + bar1.get_width()/2, bar1.get_height() + 0.02,
                f'{before_values[i]:.3f}', ha='center', va='bottom', fontsize=8, rotation=90)
        ax1.text(bar2.get_x() + bar2.get_width()/2, bar2.get_height() + 0.02,
                f'{after_values[i]:.3f}', ha='center', va='bottom', fontsize=8, rotation=90)

    # 第二個子圖：改善比例
    colors = ['green' if x > 0 else 'red' for x in improvement_ratios]
    bars3 = ax2.bar(x, improvement_ratios, color=colors, alpha=0.7)
    
    ax2.set_title(f"Improvement Ratio ({axes_str}) - % Change")
    ax2.set_xlabel(f"Features ({axes_str})")
    ax2.set_ylabel("Improvement (%)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(simplified_labels, rotation=45, ha="right")
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    # 在改善比例圖上標註數值
    for i, bar in enumerate(bars3):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, height + (1 if height >= 0 else -1),
                f'{improvement_ratios[i]:.1f}%', ha='center', 
                va='bottom' if height >= 0 else 'top', fontsize=9)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"💾 已儲存: {save_path}")

    if show:
        plt.show()
    return True

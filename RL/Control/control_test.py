# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Dict, Tuple, List, Callable, Optional, Any
from statistics import median
import math
import numpy as np

# ===== 你的現場 I/O：移動＋量測，回傳「扁平 dict」 =====
RunFn = Callable[[float, float], Dict[str, float]]

# ========== 權重、規範、限位與超參 ==========
@dataclass
class CVIWeights:
    w_trms: float = 1.0   # Time RMS
    w_tcf:  float = 0.5   # Time Crest Factor
    w_frms: float = 0.6   # Spectrum RMS
    w_fsk:  float = 0.2   # Spectrum Skewness
    w_fkurt:float = 0.3   # Spectrum Kurtosis

@dataclass
class SpecRefs:
    """A版：以『規範/基線』正規化各指標；請填入廠商允收或初始基線。"""
    time_rms: float = 2.0
    time_cf:  float = 5.0
    frms:     float = 0.02
    fskew:    float = 10.0
    fkurt:    float = 1000.0

@dataclass
class SafetyThresholds:
    time_rms_max: float = 5.0
    time_cf_max:  float = 10.0

@dataclass
class Limits:
    x_min: float; x_max: float
    y_min: float; y_max: float

@dataclass
class StepConfig:
    sig_x: float = 0.05
    sig_y: float = 0.05
    sig_x_min: float = 0.005
    sig_y_min: float = 0.005
    sig_x_max: float = 0.3
    sig_y_max: float = 0.3
    up_scale: float = 1.2
    down_scale: float = 0.8

@dataclass
class RLConfig:
    alpha: float = 0.3
    K: int = 1
    epsilon: float = 1e-3
    lambda_move: float = 0.0
    max_iters: int = 60
    no_improve_patience: int = 6
    use_rank: bool = False        # ← 切換 A（False）與 C（True）
    rank_break_ties_with_reward: bool = True  # 排名同分時用 reward 決勝

# ========== 小工具 ==========
REQUIRED_KEYS = [
    "Time_skewness_x", "Time_kurtosis_x", "Time_rms_x", "Time_crestfactor_x",
    "Powerspectrum_skewness_x", "Powerspectrum_kurtosis_x", "Powerspectrum_rms_x", "Powerspectrum_crestfactor_x",
    # "Time_skewness_y", "Time_kurtosis_y", "Time_rms_y", "Time_crestfactor_y",
    # "Powerspectrum_skewness_y", "Powerspectrum_kurtosis_y", "Powerspectrum_rms_y", "Powerspectrum_crestfactor_y",
    # "Time_skewness_z", "Time_kurtosis_z", "Time_rms_z", "Time_crestfactor_z",
    # "Powerspectrum_skewness_z", "Powerspectrum_kurtosis_z", "Powerspectrum_rms_z", "Powerspectrum_crestfactor_z"
]
# "Time_skewness_x", "Time_kurtosis_x", "Time_rms_x", "Time_crestfactor_x",
#     "Powerspectrum_skewness_x", "Powerspectrum_kurtosis_x", "Powerspectrum_rms_x", "Powerspectrum_crestfactor_x",
#     "Time_skewness_y", "Time_kurtosis_y", "Time_rms_y", "Time_crestfactor_y",
#     "Powerspectrum_skewness_y", "Powerspectrum_kurtosis_y", "Powerspectrum_rms_y", "Powerspectrum_crestfactor_y",
#     "Time_skewness_z", "Time_kurtosis_z", "Time_rms_z", "Time_crestfactor_z",
#     "Powerspectrum_skewness_z", "Powerspectrum_kurtosis_z", "Powerspectrum_rms_z", "Powerspectrum_crestfactor_z"
def _check_keys(feats: Dict[str, float]) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in feats]
    if missing:
        raise KeyError(f"run_analysis(x,y) 回傳 JSON 缺少鍵：{missing}")

def winsor(x: float, lo: Optional[float] = None, hi: Optional[float] = None) -> float:
    if lo is not None and x < lo: return lo
    if hi is not None and x > hi: return hi
    return x

def log1p_compress(x: float) -> float:
    return math.log1p(max(x, 0.0))

def _max_axis(d: Dict[str, float], base: str) -> float:
    return max(d[f"{base}_x"], d[f"{base}_y"], d[f"{base}_z"])

def _step_cost(p: Tuple[float,float], c: Tuple[float,float]) -> float:
    dx, dy = c[0]-p[0], c[1]-p[1]
    return dx*dx + dy*dy

def _unsafe(feats: Dict[str, float], thr: SafetyThresholds) -> bool:
    if _max_axis(feats, "Time_rms") > thr.time_rms_max: return True
    if _max_axis(feats, "Time_crestfactor") > thr.time_cf_max: return True
    return False

def _median_feats(batch: List[Dict[str, float]]) -> Dict[str, float]:
    """對同一候選點多次量測（K 次）逐鍵取中位數。"""
    keys = batch[0].keys()
    out: Dict[str, float] = {}
    for k in keys:
        out[k] = median([b[k] for b in batch])
    return out

# ========== A版：以 SpecRefs 正規化後組合 CVI ==========
def cvi_components_normalized(feats: Dict[str, float], refs: SpecRefs) -> Tuple[float,float,float,float,float]:
    """回傳五個已正規化且 log 壓縮後的分量：(trms_n, tcf_n, frms_n, fsk_n, fkurt_n)"""
    _check_keys(feats)
    trms  = _max_axis(feats, "Time_rms")
    tcf   = _max_axis(feats, "Time_crestfactor")
    frms  = _max_axis(feats, "Powerspectrum_rms")
    fsk   = _max_axis(feats, "Powerspectrum_skewness")
    fkurt = _max_axis(feats, "Powerspectrum_kurtosis")

    eps = 1e-12
    trms_n  = log1p_compress(trms  / max(refs.time_rms, eps))
    tcf_n   = log1p_compress(tcf   / max(refs.time_cf,  eps))
    frms_n  = log1p_compress(frms  / max(refs.frms,     eps))
    # 偏度/峰度較容易極端，做 winsor 之後再壓縮
    fsk_n   = log1p_compress(winsor(fsk  / max(refs.fskew, eps), lo=0.0, hi=1e2))
    fkurt_n = log1p_compress(winsor(fkurt/ max(refs.fkurt, eps), lo=0.0, hi=1e2))
    return trms_n, tcf_n, frms_n, fsk_n, fkurt_n

def composite_vibration_index_A(feats: Dict[str, float], w: CVIWeights, refs: SpecRefs) -> float:
    trms_n, tcf_n, frms_n, fsk_n, fkurt_n = cvi_components_normalized(feats, refs)
    return - (w.w_trms*trms_n + w.w_tcf*tcf_n + w.w_frms*frms_n + w.w_fsk*fsk_n + w.w_fkurt*fkurt_n)

def reward_from_feats_A(feats: Dict[str, float], w: CVIWeights, refs: SpecRefs, move_penalty: float = 0.0) -> float:
    # 振動越小 → CVI 越小 → reward 越大
    return  (composite_vibration_index_A(feats, w, refs) + move_penalty)

# ========== C版：加權排名法（每回合在 3 點間相對排名） ==========
def rank_aggregate_for_candidates(
    feats_list: List[Dict[str, float]],
    w: CVIWeights,
    refs: SpecRefs
) -> List[float]:
    """
    對 3 個候選點計算「加權排名分數」（越小越好）。
    先將各指標以 SpecRefs 正規化 + log1p，再各自排名後加權。
    """
    # 取各候選點的五個分量（已正規化）
    comps = [cvi_components_normalized(f, refs) for f in feats_list]
    # comps: List[Tuple[trms_n, tcf_n, frms_n, fsk_n, fkurt_n]]
    A = np.array(comps, dtype=float)  # shape (3, 5)
    # 對每個欄（指標）做由小到大排名（0=最小=最好）
    def ranks(v: np.ndarray) -> np.ndarray:
        return v.argsort().argsort()
    R_trms  = ranks(A[:,0])
    R_tcf   = ranks(A[:,1])
    R_frms  = ranks(A[:,2])
    R_fsk   = ranks(A[:,3])
    R_fkurt = ranks(A[:,4])
    R_total = (w.w_trms*R_trms + w.w_tcf*R_tcf + w.w_frms*R_frms +
               w.w_fsk*R_fsk + w.w_fkurt*R_fkurt).astype(float)
    return R_total.tolist()

# ========== 主流程（含 use_rank 開關） ==========
class Top1of3WithRunAnalysis:
    def __init__(
        self,
        run_fn: RunFn,
        start_xy: Tuple[float, float],
        limits: Limits,
        steps: StepConfig = StepConfig(),
        cfg: RLConfig = RLConfig(),
        w: CVIWeights = CVIWeights(),
        thr: SafetyThresholds = SafetyThresholds(),
        refs: SpecRefs = SpecRefs()
    ):
        self.run_fn = run_fn
        self.x, self.y = start_xy
        self.lim = limits
        self.steps = steps
        self.cfg = cfg
        self.w = w
        self.thr = thr
        self.refs = refs

        self.best_reward = -float("inf")
        self.no_improve_cnt = 0
        self.history = []  # 儲存歷史記錄供視覺化使用

    def _triangle_perturbations(self, sigx: float, sigy: float) -> List[Tuple[float, float]]:
        return [
            ( +sigx,            0.0 ),
            ( -0.5*sigx, +0.866*sigy ),
            ( -0.5*sigx, -0.866*sigy ),
        ]

    def _clip_xy(self, x: float, y: float) -> Tuple[float, float]:
        x = max(self.lim.x_min, min(self.lim.x_max, x))
        y = max(self.lim.y_min, min(self.lim.y_max, y))
        return x, y

    def _measure_feats_at(self, cx: float, cy: float, K: int) -> Tuple[Dict[str,float], bool]:
        """量測 K 次後回傳『逐鍵中位數』的 feats 與 unsafe 標誌。"""
        batch: List[Dict[str,float]] = []
        for _ in range(K):
            feats = self.run_fn(cx, cy)
            if _unsafe(feats, self.thr):
                return feats, True
            batch.append(feats)
        feats_med = batch[0] if len(batch) == 1 else _median_feats(batch)
        return feats_med, False

    def iterate(self) -> Tuple[float, float, float, Dict[str, Any]]:
        prev_xy = (self.x, self.y)
        deltas = self._triangle_perturbations(self.steps.sig_x, self.steps.sig_y)
        candidates = [ self._clip_xy(prev_xy[0]+dx, prev_xy[1]+dy) for (dx,dy) in deltas ]

        feats_list: List[Dict[str,float]] = []
        unsafe_flags: List[bool] = []
        rewards: List[float] = []

        # 量測三個候選點
        for (cx, cy) in candidates:
            feats, bad = self._measure_feats_at(cx, cy, self.cfg.K)
            unsafe_flags.append(bad)
            feats_list.append(feats)

            if bad:
                rewards.append(-1e9)
            else:
                move_penalty = self.cfg.lambda_move * _step_cost(prev_xy, (cx, cy))
                r = reward_from_feats_A(feats, self.w, self.refs, move_penalty)
                rewards.append(r)

        any_unsafe = any(unsafe_flags)
        all_unsafe = all(unsafe_flags)

        # 準備調試資訊
        debug_info = {
            'candidates': [
                {'x': candidates[i][0], 'y': candidates[i][1], 'unsafe': unsafe_flags[i], 'reward': rewards[i]}
                for i in range(len(candidates))
            ],
            'chosen': None
        }

        # 安全處理：若有不安全 → 縮步長；若全不安全 → 停在原地
        if any_unsafe:
            self.steps.sig_x = max(self.steps.sig_x * self.steps.down_scale, self.steps.sig_x_min)
            self.steps.sig_y = max(self.steps.sig_y * self.steps.down_scale, self.steps.sig_y_min)
            if all_unsafe:
                self.no_improve_cnt += 1
                print(f"[unsafe] all candidates unsafe → shrink σ, stay at ({self.x:.6f}, {self.y:.6f})")
                return self.x, self.y, self.best_reward, debug_info

        # 選點：A=連續 reward，C=加權排名
        safe_idxs = [i for i, bad in enumerate(unsafe_flags) if not bad]
        if len(safe_idxs) == 0:
            # 已在 all_unsafe 處理；保險返回
            self.no_improve_cnt += 1
            return self.x, self.y, self.best_reward, debug_info

        if self.cfg.use_rank:
            # C：加權排名（越小越好）
            rank_scores = rank_aggregate_for_candidates([feats_list[i] for i in range(3)], self.w, self.refs)
            # 只在安全集合裡選最小排名
            i_star = min(safe_idxs, key=lambda i: rank_scores[i])
            # 若同分且需要用 reward 打破平手
            if self.cfg.rank_break_ties_with_reward:
                best_rank = rank_scores[i_star]
                tied = [i for i in safe_idxs if abs(rank_scores[i] - best_rank) < 1e-9]
                if len(tied) > 1:
                    i_star = max(tied, key=lambda i: rewards[i])  # 用 reward 決勝
        else:
            # A：直接用 reward（-CVI）
            i_star = max(safe_idxs, key=lambda i: rewards[i])

        p_best = candidates[i_star]
        r_best = rewards[i_star]

        # 更新調試資訊中的選中點
        debug_info['chosen'] = {'x': p_best[0], 'y': p_best[1], 'index': i_star}

        # 步長自適應（仍用連續 reward 判斷改善）
        if r_best > self.best_reward + self.cfg.epsilon:
            self.best_reward = r_best
            self.no_improve_cnt = 0
            self.steps.sig_x = min(self.steps.sig_x * self.steps.up_scale, self.steps.sig_x_max)
            self.steps.sig_y = min(self.steps.sig_y * self.steps.up_scale, self.steps.sig_y_max)
        else:
            self.no_improve_cnt += 1
            self.steps.sig_x = max(self.steps.sig_x * self.steps.down_scale, self.steps.sig_x_min)
            self.steps.sig_y = max(self.steps.sig_y * self.steps.down_scale, self.steps.sig_y_min)

        # 位置低通 + 限位
        self.x = (1 - self.cfg.alpha) * self.x + self.cfg.alpha * p_best[0]
        self.y = (1 - self.cfg.alpha) * self.y + self.cfg.alpha * p_best[1]
        self.x, self.y = self._clip_xy(self.x, self.y)

        return self.x, self.y, self.best_reward, debug_info

    def run(self) -> Tuple[float, float, float]:
        it = 0
        while it < self.cfg.max_iters and self.no_improve_cnt < self.cfg.no_improve_patience:
            it += 1
            x, y, r, debug_info = self.iterate()
            
            # 記錄歷史資料供視覺化使用
            self.history.append({
                'iteration': it,
                'pos': {'x': x, 'y': y},
                'best_reward': r,
                'sigmas': {'x': self.steps.sig_x, 'y': self.steps.sig_y},
                'no_improve_cnt': self.no_improve_cnt,
                'debug': debug_info
            })
            
            print(f"[iter {it:02d}] pos=({x:.6f}, {y:.6f})  "
                  f"sig=({self.steps.sig_x:.6f}, {self.steps.sig_y:.6f})  "
                  f"best_r={r:.6f}  no_improve={self.no_improve_cnt}")
        return self.x, self.y, self.best_reward

# ========== 範例：如何設定與切換 ==========
if __name__ == "__main__":
    # TODO: 換成你的現場實作
    def run_analysis(x: float, y: float) -> Dict[str, float]:
        raise NotImplementedError("請用你的 run_analysis(x,y) 實作替換")

    limits = Limits(x_min=-2.0, x_max=+2.0, y_min=-2.0, y_max=+2.0)

    # A版權重（可調）
    weights = CVIWeights(w_trms=1.0, w_tcf=0.5, w_frms=0.6, w_fsk=0.2, w_fkurt=0.3)

    # 規範/基線（請改成你的廠商允收或裝配初始基準）
    refs = SpecRefs(time_rms=2.0, time_cf=5.0, frms=0.02, fskew=10.0, fkurt=1000.0)

    safety = SafetyThresholds(time_rms_max=5.0, time_cf_max=10.0)

    steps  = StepConfig(sig_x=0.5, sig_y=0.5,
                        sig_x_min=0.0005, sig_y_min=0.0005,
                        sig_x_max=2.0, sig_y_max=2.0,
                        up_scale=1.2, down_scale=0.8)

    # 切換 use_rank：False=連續 reward 模式（A），True=排名選點模式（C）
    cfg = RLConfig(alpha=0.3, K=1, epsilon=1e-3, lambda_move=0.0,
                   max_iters=15, no_improve_patience=6,
                   use_rank=True,                     # ← 這裡切換
                   rank_break_ties_with_reward=True)  # 同分時用 reward 破平手

    opt = Top1of3WithRunAnalysis(
        run_fn=run_analysis,
        start_xy=(0.0, 0.0),
        limits=limits,
        steps=steps,
        cfg=cfg,
        w=weights,
        thr=safety,
        refs=refs
    )

    # best_x, best_y, best_r = opt.run()
    # print(f"Finished at ({best_x:.6f}, {best_y:.6f}), best_reward={best_r:.6f})")

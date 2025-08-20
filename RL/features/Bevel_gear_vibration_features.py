import pandas as pd
from scipy.stats import kurtosis, skew
import numpy as np
from scipy.signal import welch
import json

def compute_feature_values_from_vibration(vibration_data: dict) -> dict:
    """從 vibration_data 字典計算特徵值，回傳 feature_values 字典。

    期望 vibration_data 內容（最少需求）：
    - vibration_data['vibration_signal']: 1D numpy array
    - vibration_data['simulation_params']['sampling_rate'] 或 vibration_data['time'] 推得 fs

    計算項目（單通道，對齊現有鍵名，以 _x 作為通道名稱）：
    - Time_skewness_x, Time_kurtosis_x, Time_rms_x, Time_crestfactor_x
    - Powerspectrum_skewness_x, Powerspectrum_kurtosis_x, Powerspectrum_rms_x, Powerspectrum_crestfactor_x
    """
    # 取得訊號
    if not isinstance(vibration_data, dict):
        raise TypeError("vibration_data 必須是 dict")

    if 'vibration_signal' not in vibration_data:
        raise KeyError("vibration_data 缺少 'vibration_signal'")
    x = np.asarray(vibration_data['vibration_signal'])
    if x.ndim != 1:
        x = np.ravel(x)

    # 取得採樣頻率 fs
    fs = None
    if 'simulation_params' in vibration_data and isinstance(vibration_data['simulation_params'], dict):
        fs = vibration_data['simulation_params'].get('sampling_rate')
    if fs is None and 'time' in vibration_data:
        t = np.asarray(vibration_data['time'])
        if len(t) >= 2:
            dt = np.mean(np.diff(t))
            if dt > 0:
                fs = 1.0 / dt
    if fs is None:
        # 合理預設值（與模擬器預設相同）
        fs = 10000.0

    # 時域特徵
    time_skew_x = float(skew(x, bias=False, nan_policy='omit'))
    time_kurt_x = float(kurtosis(x, fisher=True, bias=False, nan_policy='omit'))
    time_rms_x = float(np.sqrt(np.mean(np.square(x))))
    time_crest_x = float(np.max(np.abs(x)) / time_rms_x) if time_rms_x > 0 else float('nan')

    # 頻域特徵（Welch）
    nperseg = int(min(len(x), 8192)) if len(x) > 0 else 256
    nperseg = max(nperseg, 256)
    window = 'hann'
    noverlap = nperseg // 2
    f, Pxx = welch(x, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap, average='median')

    ps_skew_x = float(skew(Pxx, bias=False, nan_policy='omit'))
    ps_kurt_x = float(kurtosis(Pxx, fisher=True, bias=False, nan_policy='omit'))
    ps_rms_x = float(np.sqrt(np.mean(np.square(Pxx))))
    ps_crest_x = float(np.max(Pxx) / ps_rms_x) if ps_rms_x > 0 else float('nan')

    feature_values = {
        "Time_skewness_x": str(round(time_skew_x, 8)),
        "Time_kurtosis_x": str(round(time_kurt_x, 8)),
        "Time_rms_x": str(round(time_rms_x, 8)),
        "Time_crestfactor_x": str(round(time_crest_x, 8)),
        "Powerspectrum_skewness_x": str(round(ps_skew_x, 8)),
        "Powerspectrum_kurtosis_x": str(round(ps_kurt_x, 8)),
        "Powerspectrum_rms_x": str(round(ps_rms_x, 8)),
        "Powerspectrum_crestfactor_x": str(round(ps_crest_x, 8)),
        "Time_skewness_y": str(round(time_skew_x, 8)),  # Placeholder for y
        "Time_kurtosis_y": str(round(time_kurt_x, 8)),  # Placeholder for y
        "Time_rms_y": str(round(time_rms_x, 8)),        # Placeholder for y
        "Time_crestfactor_y": str(round(time_crest_x, 8)),  # Placeholder for y
        "Powerspectrum_skewness_y": str(round(ps_skew_x, 8)),  # Placeholder for y
        "Powerspectrum_kurtosis_y": str(round(ps_kurt_x, 8)),  # Placeholder for y
        "Powerspectrum_rms_y": str(round(ps_rms_x, 8)),        # Placeholder for y
        "Powerspectrum_crestfactor_y": str(round(ps_crest_x, 8)),  # Placeholder for y
        "Time_skewness_z": str(round(time_skew_x, 8)),  # Placeholder for z
        "Time_kurtosis_z": str(round(time_kurt_x, 8)),  # Placeholder for z
        "Time_rms_z": str(round(time_rms_x, 8)),        # Placeholder for z
        "Time_crestfactor_z": str(round(time_crest_x, 8)),  # Placeholder for z
        "Powerspectrum_skewness_z": str(round(ps_skew_x, 8)),  # Placeholder for z
        "Powerspectrum_kurtosis_z": str(round(ps_kurt_x, 8)),  # Placeholder for z
        "Powerspectrum_rms_z": str(round(ps_rms_x, 8)),        # Placeholder for z
        "Powerspectrum_crestfactor_z": str(round(ps_crest_x, 8)),  # Placeholder for z
    }

    return feature_values

# 讀取CSV文件
class GearDataAnalysis:
    def __init__(self, fs, Np, Ng, fPin):
        """
        初始化齒輪箱分析類別。
        :param fs: 採樣頻率 (Hz)
        :param Np: 小齒輪的齒數
        :param Ng: 大齒輪的齒數
        :param fPin: 小齒輪的旋轉頻率 (Hz)
        """
        self.fs = fs
        self.Np = Np
        self.Ng = Ng
        self.fPin = fPin
        self.fGear = self.fPin * self.Np / self.Ng  # 計算大齒輪的旋轉頻率
        self.fMesh = self.fPin * self.Np  # 計算齒輪嚙合頻率
        self.t = np.arange(0, 5, 1/self.fs)  # 產生時間序列
        self.data = None

    def Dataprocess(self, Path):
        """
        :param Path: CSV文件的路徑
        :return: 篩選出的 data_CCW 和 data_CW
        """
        data_CCW = []
        data_CW = []

        with open(Path, 'r', encoding='utf-8') as file:
            for line in file:
                # 將每一行根據逗號分割
                row = line.strip().split(',')

                # 檢查是否有至少一個欄位
                if len(row) > 0 and row[0]:  # 確保第一個欄位存在且非空
                    # 移除每一行中的空白欄位
                    row = [item for item in row if item.strip() != '']

                    # 檢查第一欄是否符合條件
                    if row[0] == 'AILocalServerTrain_Vibrate_DrivenCCW:':
                        data_CCW.append(row)
                    elif row[0] == 'AILocalServerTrain_Vibrate_DrivenCW:':
                        data_CW.append(row)

        # 確定欄位名稱，這裡你可以根據實際情況調整
        columns = ['Spindle rotation direction', 'Time', 'X', 'Y', 'Z']

        # 將篩選出的數據轉為 DataFrame
        df_CCW = pd.DataFrame(data_CCW, columns=columns)
        df_CW = pd.DataFrame(data_CW, columns=columns)

        df_CCW['X'] = pd.to_numeric(df_CCW['X'], errors='coerce')
        df_CCW['Y'] = pd.to_numeric(df_CCW['Y'], errors='coerce')
        df_CCW['Z'] = pd.to_numeric(df_CCW['Z'], errors='coerce')

        df_CW['X'] = pd.to_numeric(df_CW['X'], errors='coerce')
        df_CW['Y'] = pd.to_numeric(df_CW['Y'], errors='coerce')
        df_CW['Z'] = pd.to_numeric(df_CW['Z'], errors='coerce')
        
        return df_CCW, df_CW

    def power_spectrum_analysis(self, signal, nperseg=8192):
        """
        進行功率譜分析，使用窗函數和適當的數據段長度來改善分析質量。
        :param signal: 輸入信號陣列。
        :return: 頻率陣列和功率譜。
        """
        window = 'hann'
        noverlap = nperseg // 2
        average_method = 'median'

        f, Pxx = welch(signal, fs=self.fs, window=window, nperseg=nperseg, noverlap=noverlap, average=average_method)

        return f, Pxx


if __name__ == '__main__':
    # 範例：從 CSV 計算（原邏輯保留於 main 保護，避免 import 時自動執行）
    Path = r'M:\\_228 文毅\\CollectData_P250617001;P250617002\\CollectData_P250617001;P250617002_0001_20250702_090448.csv'

    analysis = GearDataAnalysis(fs=16384, Np=20, Ng=20, fPin=400/60)
    rpm = analysis.fPin * 60
    data_CCW, data_CW = analysis.Dataprocess(Path)

    # Time domain data feature
    Time_skewness_x = round(skew(data_CCW['X']), 8)
    Time_kurt_x = round(kurtosis(data_CCW['X']), 8)
    Time_rms_x = round(np.sqrt(np.average(np.square(data_CCW['X']))), 8)
    Time_crestfactor_x = round(np.max(data_CCW['X']) / Time_rms_x, 8)

    Time_skewness_y = round(skew(data_CCW['Y']), 8)
    Time_kurt_y = round(kurtosis(data_CCW['Y']), 8)
    Time_rms_y = round(np.sqrt(np.average(np.square(data_CCW['Y']))), 8)
    Time_crestfactor_y = round(np.max(data_CCW['Y']) / Time_rms_y, 8)

    Time_skewness_z = round(skew(data_CCW['Z']), 8)
    Time_kurt_z = round(kurtosis(data_CCW['Z']), 8)
    Time_rms_z = round(np.sqrt(np.average(np.square(data_CCW['Z']))), 8)
    Time_crestfactor_z = round(np.max(data_CCW['Z']) / Time_rms_z, 8)

    # Frequency domain data feature
    f, Powerspectrum_x = analysis.power_spectrum_analysis(data_CCW['X'], nperseg=len(data_CCW['X']))
    f, Powerspectrum_y = analysis.power_spectrum_analysis(data_CCW['Y'], nperseg=len(data_CCW['Y']))
    f, Powerspectrum_z = analysis.power_spectrum_analysis(data_CCW['Z'], nperseg=len(data_CCW['Z']))

    Powerspectrum_skewness_x = round(skew(Powerspectrum_x), 8)
    Powerspectrum_kurt_x = round(kurtosis(Powerspectrum_x), 8)
    Powerspectrum_rms_x = round(np.sqrt(np.average(np.square(Powerspectrum_x))), 8)
    Powerspectrum_crestfactor_x = round(np.max(Powerspectrum_x) / Powerspectrum_rms_x, 8)

    Powerspectrum_skewness_y = round(skew(Powerspectrum_y), 8)
    Powerspectrum_kurt_y = round(kurtosis(Powerspectrum_y), 8)
    Powerspectrum_rms_y = round(np.sqrt(np.average(np.square(Powerspectrum_y))), 8)
    Powerspectrum_crestfactor_y = round(np.max(Powerspectrum_y) / Powerspectrum_rms_y, 8)

    Powerspectrum_skewness_z = round(skew(Powerspectrum_z), 8)
    Powerspectrum_kurt_z = round(kurtosis(Powerspectrum_z), 8)
    Powerspectrum_rms_z = round(np.sqrt(np.average(np.square(Powerspectrum_z))), 8)
    Powerspectrum_crestfactor_z = round(np.max(Powerspectrum_z) / Powerspectrum_rms_z, 8)

    # 存取成json格式
    feature_values = {
        "Time_skewness_x": str(Time_skewness_x),
        "Time_kurtosis_x": str(Time_kurt_x),
        "Time_rms_x": str(Time_rms_x),
        "Time_crestfactor_x": str(Time_crestfactor_x),
        "Time_skewness_y": str(Time_skewness_y),
        "Time_kurtosis_y": str(Time_kurt_y),
        "Time_rms_y": str(Time_rms_y),
        "Time_crestfactor_y": str(Time_crestfactor_y),
        "Time_skewness_z": str(Time_skewness_z),
        "Time_kurtosis_z": str(Time_kurt_z),
        "Time_rms_z": str(Time_rms_z),
        "Time_crestfactor_z": str(Time_crestfactor_z),
        "Powerspectrum_skewness_x": str(Powerspectrum_skewness_x),
        "Powerspectrum_kurtosis_x": str(Powerspectrum_kurt_x),
        "Powerspectrum_rms_x": str(Powerspectrum_rms_x),
        "Powerspectrum_crestfactor_x": str(Powerspectrum_crestfactor_x),
        "Powerspectrum_skewness_y": str(Powerspectrum_skewness_y),
        "Powerspectrum_kurtosis_y": str(Powerspectrum_kurt_y),
        "Powerspectrum_rms_y": str(Powerspectrum_rms_y),
        "Powerspectrum_crestfactor_y": str(Powerspectrum_crestfactor_y),
        "Powerspectrum_skewness_z": str(Powerspectrum_skewness_z),
        "Powerspectrum_kurtosis_z": str(Powerspectrum_kurt_z),
        "Powerspectrum_rms_z": str(Powerspectrum_rms_z),
        "Powerspectrum_crestfactor_z": str(Powerspectrum_crestfactor_z)
    }

    # Convert the dictionary to JSON format
    json_data = json.dumps(feature_values)
    print(json_data)
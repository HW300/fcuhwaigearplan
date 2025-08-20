import sys
import os
import numpy as np

# 確保測試執行時能找到 local package
project_dir = os.path.dirname(__file__)
if project_dir not in sys.path:
	sys.path.insert(0, project_dir)

from control_environment import run_analysis_and_get_time_signal


def test_run_analysis_returns_time_and_signal():
	t, s = run_analysis_and_get_time_signal(24, -31)
	# 檢查型別
	assert isinstance(t, np.ndarray)
	assert isinstance(s, np.ndarray)
	# 長度一致且大於0
	assert len(t) == len(s)
	assert len(t) > 0
	# 基本頻域特性：訊號不是全零
	assert not np.allclose(s, 0)


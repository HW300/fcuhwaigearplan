#!/usr/bin/env python3
"""
整合測試腳本：同時管理 A-client (RL) 和 B-client (模擬器)
"""

import subprocess
import time
import signal
import sys
import os
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegratedTestRunner:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_b_client(self):
        """啟動 B-client 模擬器"""
        logger.info("🚀 啟動 B-client 模擬器...")
        try:
            b_process = subprocess.Popen(
                [sys.executable, "simulated_b_client.py"],
                cwd=os.path.dirname(__file__),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            self.processes.append(("B-client", b_process))
            
            # 在獨立線程中讀取 B-client 輸出
            def read_b_output():
                for line in iter(b_process.stdout.readline, ''):
                    if line.strip():
                        logger.info(f"[B] {line.strip()}")
                        
            threading.Thread(target=read_b_output, daemon=True).start()
            return True
            
        except Exception as e:
            logger.error(f"❌ 啟動 B-client 失敗: {e}")
            return False
            
    def start_a_client(self):
        """啟動 A-client RL 客戶端"""
        logger.info("🚀 啟動 A-client RL 客戶端...")
        try:
            a_process = subprocess.Popen(
                [sys.executable, "test_RL_network.py"],
                cwd=os.path.dirname(__file__),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            self.processes.append(("A-client", a_process))
            
            # 在獨立線程中讀取 A-client 輸出
            def read_a_output():
                for line in iter(a_process.stdout.readline, ''):
                    if line.strip():
                        logger.info(f"[A] {line.strip()}")
                        
            threading.Thread(target=read_a_output, daemon=True).start()
            return True
            
        except Exception as e:
            logger.error(f"❌ 啟動 A-client 失敗: {e}")
            return False
            
    def send_start_signal(self):
        """向 B-client 發送 START 命令"""
        b_process = None
        for name, process in self.processes:
            if name == "B-client" and process.poll() is None:
                b_process = process
                break
                
        if b_process:
            try:
                # 向 B-client 的 stdin 發送 's' 命令
                b_process.stdin.write('s\n')
                b_process.stdin.flush()
                logger.info("📤 已向 B-client 發送 START 命令")
                return True
            except Exception as e:
                logger.error(f"❌ 發送 START 命令失敗: {e}")
                return False
        else:
            logger.error("❌ 找不到運行中的 B-client")
            return False
            
    def send_stop_signal(self):
        """向 B-client 發送 STOP 命令"""
        b_process = None
        for name, process in self.processes:
            if name == "B-client" and process.poll() is None:
                b_process = process
                break
                
        if b_process:
            try:
                b_process.stdin.write('stop\n')
                b_process.stdin.flush()
                logger.info("🛑 已向 B-client 發送 STOP 命令")
                return True
            except Exception as e:
                logger.error(f"❌ 發送 STOP 命令失敗: {e}")
                return False
        else:
            logger.error("❌ 找不到運行中的 B-client")
            return False
            
    def check_processes(self):
        """檢查進程狀態"""
        active_processes = []
        for name, process in self.processes:
            if process.poll() is None:
                active_processes.append((name, process))
            else:
                logger.warning(f"⚠️ {name} 進程已結束")
                
        self.processes = active_processes
        return len(active_processes)
        
    def cleanup(self):
        """清理所有進程"""
        logger.info("🧹 清理進程...")
        for name, process in self.processes:
            if process.poll() is None:
                logger.info(f"終止 {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"強制終止 {name}")
                    process.kill()
        self.processes.clear()
        
    def run_interactive(self):
        """執行互動式測試"""
        logger.info("=== RL 網路測試整合系統 ===")
        
        # 啟動 B-client
        if not self.start_b_client():
            return
            
        # 等待 B-client 穩定
        time.sleep(3)
        
        # 啟動 A-client  
        if not self.start_a_client():
            self.cleanup()
            return
            
        # 等待 A-client 穩定
        time.sleep(3)
        
        logger.info("✅ 兩個客戶端都已啟動")
        logger.info("💡 可用命令:")
        logger.info("   'start' 或 's': 開始 RL 優化")
        logger.info("   'stop': 停止 RL 優化")
        logger.info("   'status': 檢查進程狀態")
        logger.info("   'quit' 或 'q': 退出")
        
        # 互動式控制循環
        while self.running:
            try:
                cmd = input(">>> ").strip().lower()
                
                if cmd in ['start', 's']:
                    self.send_start_signal()
                elif cmd == 'stop':
                    self.send_stop_signal()
                elif cmd == 'status':
                    active_count = self.check_processes()
                    logger.info(f"🔍 活動進程數: {active_count}")
                    for name, _ in self.processes:
                        logger.info(f"   ✅ {name}")
                elif cmd in ['quit', 'q']:
                    break
                else:
                    logger.info("❓ 未知命令")
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as e:
                logger.error(f"❌ 命令處理錯誤: {e}")
                
        self.running = False
        self.cleanup()

def signal_handler(signum, frame):
    """信號處理器"""
    logger.info("收到退出信號...")
    sys.exit(0)

def main():
    # 註冊信號處理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    runner = IntegratedTestRunner()
    
    try:
        runner.run_interactive()
    except Exception as e:
        logger.error(f"❌ 執行錯誤: {e}")
    finally:
        runner.cleanup()
        logger.info("👋 測試完成")

if __name__ == "__main__":
    main()

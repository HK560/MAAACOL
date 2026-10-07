"""
Ace Combat Online - TDM 自动化游玩脚本
基于 MaaFramework 架构设计 (Dispatcher 调度器模式)
"""

import argparse
import ctypes
import os
import random
import sys
import time

from maa.controller import Win32Controller
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum
from maa.resource import Resource
from maa.tasker import Tasker
from maa.toolkit import Toolkit

# 引入独立输入控制器与会话跟踪器
from game_input import GameInputController, session_tracker

# Win32 辅助
user32 = ctypes.windll.user32


def ensure_desktop():
    """确保线程能够访问默认桌面"""
    h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    if h_desk:
        user32.SetThreadDesktop(h_desk)


def parse_args():
    parser = argparse.ArgumentParser(description="Ace Combat Online TDM Runner")
    parser.add_argument(
        "--rounds",
        type=int,
        nargs="?",
        const=10,
        default=10,
        help="目标完成场次 (默认 10 场，设为 0 表示不限)",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        nargs="?",
        const=60,
        default=60,
        help="最长运行分钟数 (默认 60 分钟，设为 0 表示不限)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="是否开启调试模式",
    )
    return parser.parse_args()


class TdmAutomator:
    def __init__(self, max_rounds: int = 10, max_minutes: int = 60, debug: bool = False):
        self.max_rounds = max_rounds
        self.max_minutes = max_minutes
        self.debug = debug

        self.res = None
        self.ctrl = None
        self.tasker = None
        self.hwnd = None

        # 战局状态记忆
        self.in_battle = False
        self.battle_start_time = 0
        self.last_battle_time = 0
        self.last_state_name = "Unknown"

    def setup(self) -> bool:
        ensure_desktop()

        print("[Init] 正在初始化 MaaFramework Toolkit...")
        Toolkit.init_option("./")

        self.res = Resource()
        bundle_job = self.res.post_bundle("./assets/resource")
        bundle_job.wait()
        if not self.res.loaded:
            print("[Init] 资源加载失败 (assets/resource).")
            return False

        self.hwnd = GameInputController.get_game_hwnd()
        if not self.hwnd:
            print("[Init] 未找到游戏窗口！请确保 Ace Combat 8 正在运行。")
            return False

        print(f"[Init] 找到游戏窗口: HWND={self.hwnd:#x}")

        self.ctrl = Win32Controller(
            self.hwnd,
            MaaWin32ScreencapMethodEnum.PrintWindow.value,
            MaaWin32InputMethodEnum.PostMessage.value,
            MaaWin32InputMethodEnum.PostMessage.value,
        )
        self.ctrl.post_connection().wait()

        self.tasker = Tasker()
        self.tasker.bind(self.res, self.ctrl)

        session_tracker.reset(self.max_rounds, self.max_minutes)
        print(
            f"[Init] 初始化就绪！目标场次: {self.max_rounds} 局，时长限制: {self.max_minutes} 分钟。"
        )
        return True

    def dispatch_state(self) -> str:
        """通过 StartTDM 统一调度识别当前画面所处状态"""
        job = self.tasker.post_task("StartTDM")
        detail = job.wait().get()
        if not detail or not detail.nodes:
            return "Unknown"

        # 若命中提示或错误弹窗 (选项 OK)，优先返回处理
        for node in detail.nodes:
            if node.name == "CheckDialogOk" and node.completed:
                return "CheckDialogOk"

        # 取最后一个命中的有效节点
        for node in reversed(detail.nodes):
            if node.name != "StartTDM" and node.completed:
                return node.name
        return "Unknown"

    def is_in_lobby(self) -> bool:
        """快速轻量检查当前画面是否已回到大厅 (仅检测单节点，耗时极低)"""
        if not self.tasker:
            return False
        job = self.tasker.post_task("CheckLobby")
        detail = job.wait().get()
        if not detail or not detail.nodes:
            return False
        for node in detail.nodes:
            if node.name == "CheckLobby" and node.completed:
                return True
        return False

    def run_loop(self):
        print("\n================ TDM 自动化对战已启动 ================")
        print("按 Ctrl + C 可随时安全终止运行。\n")

        try:
            while True:
                ensure_desktop()

                # 检查是否满足停止条件
                if session_tracker.check_stop_condition():
                    print("\n[TdmAutomator] 设定条件已满足，任务顺利完成！")
                    break

                # 统一识别当前画面状态
                state = self.dispatch_state()

                # 0. 处于提示或错误弹窗 (选项 OK)
                if state == "CheckDialogOk":
                    if self.last_state_name != "DialogOk":
                        print("[State] 检测到提示/错误弹窗 (选项 OK)，确认并关闭 (按空格)...")
                        self.last_state_name = "DialogOk"

                    GameInputController.send_key("space", 0.1)
                    time.sleep(1.0)
                    continue

                # 1. 处于游戏最外层主菜单 (Main Menu)
                if state == "CheckMainMenu":
                    if self.in_battle:
                        battle_dur = (
                            time.time() - self.battle_start_time
                            if self.battle_start_time
                            else 0
                        )
                        print(
                            f"[State] ⚠ 检测到从战局异常掉回主菜单 (历时 {battle_dur:.0f}s)，正在自愈恢复..."
                        )
                        self.in_battle = False
                        self.battle_start_time = 0
                        self.last_battle_time = 0

                    if self.last_state_name != "MainMenu":
                        print("[State] 处于主菜单，重新进入 ACE COMBAT ONLINE (按空格)...")
                        self.last_state_name = "MainMenu"

                    GameInputController.send_key("space", 0.1)
                    time.sleep(2.5)
                    continue

                # 2. 处于大厅界面 (Lobby)
                if state == "CheckLobby":
                    # 若此前正在对局中，说明刚刚打完结算回到了大厅
                    if self.in_battle:
                        self.in_battle = False
                        battle_dur = (
                            time.time() - self.battle_start_time
                            if self.battle_start_time
                            else 0
                        )
                        self.battle_start_time = 0

                        # 判断是否为正常完成对局还是过短异常退出
                        if battle_dur >= 45:
                            session_tracker.increment_round()
                            print(
                                f"\n[Result] ★ 本局已顺利完成并返回大厅 (历时 {battle_dur:.0f}s)！当前累计完成: {session_tracker.completed_rounds} 局"
                            )
                        else:
                            print(
                                f"\n[Result] ⚠ 本局仅持续 {battle_dur:.0f}s 即返回大厅 (疑似异常中断)，不计入有效场次。"
                            )

                        # 结算后检查一次是否该停止
                        if session_tracker.check_stop_condition():
                            print("[TdmAutomator] 已达到目标局数或时长，停止出击。")
                            break
                        time.sleep(2.0)

                    if self.last_state_name != "Lobby":
                        if self.last_state_name in (
                            "Matching",
                            "RoomSelectSet",
                            "ConfirmSlot",
                            "DialogOk",
                        ):
                            print(
                                f"[State] ⚠ 检测到从 [{self.last_state_name}] 异常掉回多人大厅，重新打开在线菜单并重新出击 (按 Tab)..."
                            )
                        else:
                            print("[State] 处于游戏大厅，打开在线菜单 (按 Tab)...")
                        self.last_state_name = "Lobby"

                    GameInputController.send_key("tab", 0.1)
                    time.sleep(1.0)
                    continue

                # 2. 处于在线菜单 (OnlineMenu)
                if state == "CheckOnlineMenu":
                    if self.last_state_name != "OnlineMenu":
                        print("[State] 处于在线菜单，进入 MISSIONS (按空格)...")
                        self.last_state_name = "OnlineMenu"

                    GameInputController.send_key("space", 0.1)
                    time.sleep(1.0)
                    continue

                # 3. 处于任务出击菜单 (MissionsMenu)
                if state == "CheckMissionsMenu":
                    if self.last_state_name != "MissionsMenu":
                        print("[State] 处于任务菜单，确认出击 SORTIE (按空格)...")
                        self.last_state_name = "MissionsMenu"

                    GameInputController.send_key("space", 0.1)
                    time.sleep(1.5)
                    continue

                # 4. 处于等待匹配中 (Matching)
                if state in ("CheckMatchingTop", "CheckMatchingBottom"):
                    if self.last_state_name != "Matching":
                        print("[State] 正在等待匹配中 (显示: 等待匹配 / 取消匹配)，静默等待分配房间...")
                        self.last_state_name = "Matching"

                    time.sleep(1.5)
                    continue

                # 5. 处于机体出击确认弹窗 (Confirm Slot / YES)
                if state == "CheckConfirmSlot":
                    if self.last_state_name != "ConfirmSlot":
                        print("[State] 弹出机体组合确认弹窗，确认出击 YES (按空格)...")
                        self.last_state_name = "ConfirmSlot"

                    GameInputController.send_key("space", 0.1)
                    time.sleep(1.0)
                    continue

                # 6. 处于出击准备房间 (| SELECT SET |)
                if state == "CheckRoomSelectSet":
                    if self.last_state_name != "RoomSelectSet":
                        print("[State] 进入出击准备房间，选择机体并保持确认 (固定间隔按空格)...")
                        self.last_state_name = "RoomSelectSet"

                    GameInputController.send_key("space", 0.1)
                    time.sleep(1.2)
                    continue

                # 7. 处于战局中 (InBattle)
                if state == "CheckInBattle":
                    if not self.in_battle:
                        print("[State] 战斗开始！进入局内巡航与防挂机状态 (WASD 机动 + 固定间隔按空格)...")
                        self.in_battle = True
                        self.battle_start_time = time.time()
                        self.last_state_name = "InBattle"

                    self.last_battle_time = time.time()

                    # 周期性执行轻度机动防踢
                    actions = ["w", "a", "d", "s"]
                    key = random.choice(actions)
                    hold = random.uniform(0.1, 0.25)
                    GameInputController.send_key(key, hold)
                    time.sleep(0.2)
                    # 同时固定间隔点按一次空格
                    GameInputController.send_key("space", 0.08)
                    time.sleep(1.5)
                    continue

                # 8. 未识别到上述特征 (战局结束、结算统计或转场黑屏)
                if self.in_battle:
                    time_since_battle = time.time() - self.last_battle_time
                    # 战局刚脱离战斗 HUD 即视为进入结算阶段 (快速响应)
                    if time_since_battle > 0.8:
                        if self.last_state_name != "SkippingResult":
                            print("[State] 战局已结束，正在快速连按空格跳过多重结算动画...")
                            self.last_state_name = "SkippingResult"

                        # 结算界面通常包含战果、得分榜、经验/奖励等多层页面，需要连续按好几个空格
                        # 采用高频连打机制，每次连续快速点按，并实时检测是否已提前返回大厅
                        for _ in range(6):
                            GameInputController.send_key("space", 0.05)
                            time.sleep(0.08)
                            if self.is_in_lobby():
                                break
                        continue

                # 默认轻度等待
                time.sleep(0.8)

        except KeyboardInterrupt:
            print("\n[TdmAutomator] 收到中断信号，安全停止。")


def main():
    args = parse_args()
    automator = TdmAutomator(
        max_rounds=args.rounds,
        max_minutes=args.minutes,
        debug=args.debug,
    )
    if automator.setup():
        automator.run_loop()


if __name__ == "__main__":
    main()

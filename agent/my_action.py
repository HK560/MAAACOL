import json
import os
import random
import sys
import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

# 从根目录导入输入控制器、会话跟踪器与自动化调度器
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game_input import GameInputController, session_tracker
from run_tdm import TdmAutomator


@AgentServer.custom_action("start_tdm_runner")
class StartTdmRunnerAction(CustomAction):
    """GUI 触发的 TDM 自动化对战挂机任务入口动作"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = {}
        if argv.custom_action_param:
            try:
                if isinstance(argv.custom_action_param, dict):
                    param = argv.custom_action_param
                else:
                    param = json.loads(argv.custom_action_param)
            except Exception as e:
                print(f"[StartTdmRunnerAction] 参数解析异常: {e}，将采用默认配置")

        max_rounds = int(param.get("max_rounds", 10))
        max_minutes = int(param.get("max_minutes", 60))

        print(
            f"[StartTdmRunnerAction] GUI 任务已触发：目标场次={max_rounds}, 最长时长={max_minutes}分钟"
        )

        automator = TdmAutomator(
            max_rounds=max_rounds,
            max_minutes=max_minutes,
            context=context,
        )
        return automator.run_loop()


@AgentServer.custom_action("send_game_key")
class SendGameKeyAction(CustomAction):
    """发送游戏按键动作"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = json.loads(argv.custom_action_param or "{}") or {}
        key = param.get("key", "space")
        hold = float(param.get("hold", 0.08))
        sleep_after = float(param.get("sleep_after", 0.2))

        print(f"[SendGameKeyAction] Pressing key: {key} (hold={hold}s)")
        success = GameInputController.send_key(key, hold)
        if sleep_after > 0:
            time.sleep(sleep_after)
        return success


@AgentServer.custom_action("battle_anti_idle")
class BattleAntiIdleAction(CustomAction):
    """战局内防挂机轻微操作动作"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        print("[BattleAntiIdleAction] Performing anti-idle maneuver...")
        actions = ["w", "a", "d", "s"]
        chosen_key = random.choice(actions)
        hold_time = random.uniform(0.1, 0.3)
        GameInputController.send_key(chosen_key, hold_time)
        return True


@AgentServer.custom_action("on_round_completed")
class OnRoundCompletedAction(CustomAction):
    """战局结算完毕后增加计数并检查停止条件"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = json.loads(argv.custom_action_param or "{}") or {}
        if "max_rounds" in param:
            session_tracker.max_rounds = int(param["max_rounds"])
        if "max_minutes" in param:
            session_tracker.max_minutes = int(param["max_minutes"])

        session_tracker.increment_round()

        if session_tracker.check_stop_condition():
            print("[OnRoundCompletedAction] Stopping task as conditions met.")
            context.tasker.post_stop()
            return False

        return True

import os
import sys

# 将工程根目录添加到模块搜索路径，确保可以直接导入根目录的 run_tdm 与 game_input
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 便携版 Python(embeddable) 自带 ._pth 会跳过脚本目录，需显式补上以保证 my_action / my_reco 可导入
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)


class _GuiLogStream:
    """把 Agent 的标准输出改写成 MFAAvalonia 日志面板能识别的格式

    MFAAvalonia 只会把带等级前缀（info:/warn:/err: 等）的 Agent 输出显示到 GUI 日志面板，
    普通 print 仅写入日志文件；同时它给子进程追加 -u 的判断依赖参数以 .py 结尾，
    而脚本路径带引号时会判定失败，导致 stdout 处于块缓冲、面板长时间看不到具体步骤。
    这里统一补前缀并逐行刷新，让 run_tdm / my_action 中的 print 实时出现在 GUI 日志里。
    """

    # MaaProcessor 识别的等级前缀，命中任意一个就认为调用方已自带等级
    LEVEL_PREFIXES = (
        "trace:",
        "debug:",
        "success:",
        "info:",
        "warn:",
        "warning:",
        "err:",
        "error:",
        "critical:",
    )

    def __init__(self, stream, default_prefix: str):
        self._stream = stream
        self._default_prefix = default_prefix
        self._pending = ""

    def write(self, text: str) -> int:
        # 统一换行符后再按行切分，保证 \r 类进度输出同样能及时送出
        self._pending += text.replace("\r\n", "\n").replace("\r", "\n")
        *lines, self._pending = self._pending.split("\n")
        for line in lines:
            self._emit(line)
        return len(text)

    def _emit(self, line: str) -> None:
        if line.strip() and not line.startswith(self.LEVEL_PREFIXES):
            line = f"{self._default_prefix}{line}"
        self._stream.write(f"{line}\n")
        self._stream.flush()

    def flush(self) -> None:
        if self._pending:
            line, self._pending = self._pending, ""
            self._emit(line)
        self._stream.flush()

    def __getattr__(self, name):
        # 其余属性（encoding / isatty / buffer 等）透传给原始流
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._stream, name)


def _setup_gui_log_bridge():
    """接入 GUI 日志桥：编码容错 + 补等级前缀 + 逐行刷新"""
    for name, default_prefix in (("stdout", "info: "), ("stderr", "err: ")):
        stream = getattr(sys, name)
        if hasattr(stream, "reconfigure"):
            # GUI 侧已强制 UTF-8，这里兜底避免非 UTF-8 控制台下的编码异常
            stream.reconfigure(encoding="utf-8", errors="replace")
        setattr(sys, name, _GuiLogStream(stream, default_prefix))


_setup_gui_log_bridge()


from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit

import my_action
import my_reco


def main():
    Toolkit.init_option("./")

    if len(sys.argv) < 2:
        print("Usage: python main.py <socket_id>")
        print("socket_id is provided by AgentIdentifier.")
        sys.exit(1)

    socket_id = sys.argv[-1]

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()

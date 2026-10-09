from pathlib import Path

import shutil
import sys

import json

def strip_jsonc_comments(text: str) -> str:
    result = []
    i, n = 0, len(text)
    in_string, escape = False, False
    while i < n:
        c = text[i]
        if in_string:
            result.append(c)
            if escape: escape = False
            elif c == "\\": escape = True
            elif c == '"': in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            result.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n:
            next_c = text[i + 1]
            if next_c == "/":
                i += 2
                while i < n and text[i] not in "\r\n": i += 1
                continue
            elif next_c == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"): i += 1
                i += 2
                continue
        result.append(c)
        i += 1
    return "".join(result)

class _JsoncFallback:
    @staticmethod
    def load(fp):
        clean_text = strip_jsonc_comments(fp.read())
        return json.loads(clean_text)
    @staticmethod
    def dump(obj, fp, **kwargs):
        return json.dump(obj, fp, **kwargs)

try:
    import jsonc
except ModuleNotFoundError:
    jsonc = _JsoncFallback

from configure import configure_ocr_model
from embedded_python import install_embedded_python, verify_agent_env
from embed_runtime import install_embedded_dotnet, install_vc_runtime


working_dir = Path(__file__).parent.parent.resolve()
install_path = working_dir / Path("install")
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"

# the first parameter is self name
if sys.argv.__len__() < 4:
    print("Usage: python install.py <version> <os> <arch>")
    print("Example: python install.py v1.0.0 win x86_64")
    sys.exit(1)

os_name = sys.argv[2]
arch = sys.argv[3]


def get_dotnet_platform_tag():
    """自动检测当前平台并返回对应的dotnet平台标签"""
    if os_name == "win" and arch == "x86_64":
        platform_tag = "win-x64"
    elif os_name == "win" and arch == "aarch64":
        platform_tag = "win-arm64"
    elif os_name == "macos" and arch == "x86_64":
        platform_tag = "osx-x64"
    elif os_name == "macos" and arch == "aarch64":
        platform_tag = "osx-arm64"
    elif os_name == "linux" and arch == "x86_64":
        platform_tag = "linux-x64"
    elif os_name == "linux" and arch == "aarch64":
        platform_tag = "linux-arm64"
    else:
        print("Unsupported OS or architecture.")
        print("available parameters:")
        print("version: e.g., v1.0.0")
        print("os: [win, macos, linux, android]")
        print("arch: [aarch64, x86_64]")
        sys.exit(1)

    return platform_tag


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print('请先下载 MaaFramework 到 "deps"。')
        sys.exit(1)

    if os_name == "android":
        shutil.copytree(
            working_dir / "deps" / "bin",
            install_path,
            dirs_exist_ok=True,
        )
        shutil.copytree(
            working_dir / "deps" / "share" / "MaaAgentBinary",
            install_path / "MaaAgentBinary",
            dirs_exist_ok=True,
        )
    else:
        shutil.copytree(
            working_dir / "deps" / "bin",
            install_path / "runtimes" / get_dotnet_platform_tag() / "native",
            ignore=shutil.ignore_patterns(
                "*MaaDbgControlUnit*",
                "*MaaThriftControlUnit*",
                "*MaaRpc*",
                "*MaaHttp*",
                "plugins",
                "*.node",
                "*MaaPiCli*",
            ),
            dirs_exist_ok=True,
        )
        shutil.copytree(
            working_dir / "deps" / "share" / "MaaAgentBinary",
            install_path / "libs" / "MaaAgentBinary",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            working_dir / "deps" / "bin" / "plugins",
            install_path / "plugins" / get_dotnet_platform_tag(),
            dirs_exist_ok=True,
        )



def install_resource():

    configure_ocr_model()

    # 便携 Python：内置解释器与依赖，使 Agent 与 CLI 不依赖主机环境
    standalone = install_embedded_python(
        install_path,
        working_dir / ".cache" / "embedded-python",
        working_dir / "requirements.txt",
        arch,
    )
    if not standalone:
        print("[WARN] 便携 Python 组装失败，Agent 将回退使用主机 python")
    else:
        # 自检：解释器能导入 maa.agent，且原生运行时与绑定同源；任一项不通过直接失败，避免发布不可用产物
        verify_agent_env(install_path)

    # .NET 运行时与 VC++ 运行库同样随包分发：上游 MFAAvalonia 是框架依赖发布，主机缺少运行时时 GUI 无法启动
    if get_dotnet_platform_tag() == "win-x64":
        if not install_embedded_dotnet(install_path, working_dir / ".cache" / "embedded-dotnet"):
            print("[WARN] .NET 运行时组装失败，GUI 将回退使用主机 .NET 运行时")
        install_vc_runtime(install_path)

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )
    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = jsonc.load(f)

    interface["version"] = version
    # 指向包内便携 Python，保证解压后可直接运行
    if "agent" in interface:
        interface["agent"]["child_exec"] = "./python/python.exe" if standalone else "python"

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        jsonc.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    shutil.copy2(
        working_dir / "README.md",
        install_path,
    )
    shutil.copy2(
        working_dir / "LICENSE",
        install_path,
    )


def install_agent():
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )


def install_scripts():
    # requirements.txt 需随包分发，供 ensure_agent_env.bat 提示用户安装依赖
    for script_name in ["game_input.py", "run_tdm.py", "requirements.txt"]:
        src = working_dir / script_name
        if src.exists():
            shutil.copy2(src, install_path)

    # Python 环境自检脚本（启动脚本会调用它选择带 maafw 的解释器）
    shutil.copy2(working_dir / "tools" / "ensure_agent_env.bat", install_path)


def install_gui_executable():
    """将 GUI 主程序重命名为 MAAACOL (支持 Windows 与 Unix)"""
    mfa_win = install_path / "MFAAvalonia.exe"
    target_win = install_path / "MAAACOL.exe"
    if mfa_win.exists():
        shutil.copy2(mfa_win, target_win)
        mfa_win.unlink(missing_ok=True)

    mfa_unix = install_path / "MFAAvalonia"
    target_unix = install_path / "MAAACOL"
    if mfa_unix.exists():
        shutil.copy2(mfa_unix, target_unix)
        mfa_unix.unlink(missing_ok=True)

    # 清理非标准/中文批处理脚本 (如 DependencySetup_依赖安装_win.bat)
    for bf in install_path.glob("*.bat"):
        try:
            bf.name.encode("ascii")
        except UnicodeEncodeError:
            bf.unlink(missing_ok=True)


def install_launcher_scripts():
    """生成纯 ASCII 英文启动脚本"""
    start_gui_bat = install_path / "start_gui.bat"
    start_gui_content = r"""@echo off
title MAAACOL - Graphical Interface (GUI)
echo =======================================================
echo          Starting MAAACOL Graphical Interface (GUI)
echo =======================================================
echo.
call "%~dp0ensure_agent_env.bat" "%~dp0."
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)
:: Prefer the .NET runtime shipped inside the package, so no host .NET install is required
if exist "%~dp0runtime\shared" (
    set "DOTNET_ROOT=%~dp0runtime"
    set "DOTNET_ROOT_X64=%~dp0runtime"
)
echo [INFO] Launching MAAACOL.exe...
start "" "%~dp0MAAACOL.exe"
"""
    with open(start_gui_bat, "w", encoding="ascii", newline="\r\n") as f:
        f.write(start_gui_content)

    run_bat = install_path / "run_tdm.bat"
    run_bat_content = """@echo off
title MAAACOL - Multiplayer Battle Runner
echo =======================================================
echo        Ace Combat Online - Multiplayer Battle Runner
echo =======================================================
echo.
echo [Pre-requisite Instructions]
echo 1. Manually enter Multiplayer mode in game.
echo 2. Choose your desired game mode (any mode supported).
echo 3. Return to Multiplayer Lobby (where your character can freely move).
echo 4. Configure rounds and max duration below to start.
echo [Recommendation] Strongly recommend setting game to Windowed 1280x720 resolution.
echo.

call "%~dp0ensure_agent_env.bat" "%~dp0."
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)

set ROUNDS=10
set MINUTES=60

set /p USER_ROUNDS="Target rounds [Default 10, 0 for unlimited]: "
if not "%USER_ROUNDS%"=="" set ROUNDS=%USER_ROUNDS%

set /p USER_MINUTES="Max minutes [Default 60, 0 for unlimited]: "
if not "%USER_MINUTES%"=="" set MINUTES=%USER_MINUTES%

echo.
echo Starting: rounds=%ROUNDS%, max_minutes=%MINUTES%...
echo Press Ctrl+C anytime to stop.
echo.

python run_tdm.py --rounds %ROUNDS% --minutes %MINUTES%

echo.
pause
"""
    with open(run_bat, "w", encoding="ascii", newline="\r\n") as f:
        f.write(run_bat_content)


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    install_scripts()
    install_gui_executable()
    install_launcher_scripts()

    print(f"Install to {install_path} successfully.")

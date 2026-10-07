"""
MAAACOL 本地打包构建脚本 (Local Build & Package Script)
支持：
  1. 极速打包 (基于本地已有运行环境/gui目录，推荐日常使用)
  2. 干净全量打包 (从 GitHub 下载或使用 deps 干净组装)
  3. 快速同步最新资源至本地 gui 调试目录
"""

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

# 配置 Windows 控制台 UTF-8 与 ANSI 颜色
if sys.platform == "win32":
    os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def strip_jsonc_comments(text: str) -> str:
    """纯 Python 实现的 JSONC 注释剥离器，无需额外依赖"""
    result = []
    i = 0
    n = len(text)
    in_string = False
    escape = False

    while i < n:
        c = text[i]
        if in_string:
            result.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
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
                while i < n and text[i] not in "\r\n":
                    i += 1
                continue
            elif next_c == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue

        result.append(c)
        i += 1

    return "".join(result)


def load_jsonc_file(file_path: Path) -> dict:
    """加载带注释的 JSON 文件"""
    try:
        import jsonc
        with open(file_path, "r", encoding="utf-8") as f:
            return jsonc.load(f)
    except Exception:
        with open(file_path, "r", encoding="utf-8") as f:
            clean_text = strip_jsonc_comments(f.read())
            return json.loads(clean_text)


ROOT_DIR = Path(__file__).parent.parent.resolve()
TOOLS_DIR = ROOT_DIR / "tools"
ASSETS_DIR = ROOT_DIR / "assets"
GUI_DIR = ROOT_DIR / "gui"
DIST_DIR = ROOT_DIR / "dist"


def log_info(msg: str):
    print(f"\033[32m[INFO]\033[0m {msg}")


def log_warn(msg: str):
    print(f"\033[33m[WARN]\033[0m {msg}")


def log_error(msg: str):
    print(f"\033[31m[ERROR]\033[0m {msg}")


def log_step(title: str):
    print(f"\n\033[36m=== {title} ===\033[0m")


def get_current_version() -> str:
    """从 assets/interface.json 读取当前版本号"""
    interface_path = ASSETS_DIR / "interface.json"
    if interface_path.exists():
        try:
            data = load_jsonc_file(interface_path)
            ver = str(data.get("version", "0.1.0")).strip()
            if not ver.startswith("v"):
                ver = f"v{ver}"
            return ver
        except Exception as e:
            log_warn(f"读取 interface.json 版本失败: {e}")
    return "v0.1.0"


def detect_system() -> tuple[str, str]:
    """检测当前操作系统与CPU架构"""
    sys_name = platform.system().lower()
    if sys_name == "windows":
        os_name = "win"
    elif sys_name == "darwin":
        os_name = "macos"
    elif sys_name == "linux":
        os_name = "linux"
    else:
        os_name = "win"

    machine = platform.machine().lower()
    if machine in ["amd64", "x86_64"]:
        arch = "x86_64"
    elif machine in ["arm64", "aarch64"]:
        arch = "aarch64"
    else:
        arch = "x86_64"

    return os_name, arch


def create_launcher_scripts(target_dir: Path):
    """为打包目录创建友好的双击启动脚本"""
    # 1. 启动图形界面UI.bat
    gui_bat = target_dir / "启动图形界面UI.bat"
    gui_bat_content = """@echo off
title MAAACOL - GUI
echo 正在启动 MAAACOL 图形界面...
start "" "%~dp0MFAAvalonia.exe"
"""
    with open(gui_bat, "w", encoding="gbk", newline="\r\n") as f:
        f.write(gui_bat_content)

    # 2. 启动TDM脚本.bat
    tdm_bat = target_dir / "启动TDM脚本.bat"
    tdm_bat_content = """@echo off
title MAAACOL - TDM Runner
echo =======================================================
echo          Ace Combat Online - TDM Automation Runner
echo =======================================================
echo.
echo [提示] 请确保游戏运行在 1280x720 分辨率下。
echo.

set ROUNDS=10
set MINUTES=60

set /p USER_ROUNDS="运行局数 [默认 10, 输入 0 为无限制]: "
if not "%USER_ROUNDS%"=="" set ROUNDS=%USER_ROUNDS%

set /p USER_MINUTES="运行最长分钟数 [默认 60, 输入 0 为无限制]: "
if not "%USER_MINUTES%"=="" set MINUTES=%USER_MINUTES%

echo.
echo 启动中: 局数=%ROUNDS%, 最长=%MINUTES%分钟...
echo 按 Ctrl+C 可随时停止。
echo.

python run_tdm.py --rounds %ROUNDS% --minutes %MINUTES%

echo.
pause
"""
    with open(tdm_bat, "w", encoding="gbk", newline="\r\n") as f:
        f.write(tdm_bat_content)


def zip_directory(source_dir: Path, output_zip_path: Path):
    """将目标目录压缩为 zip"""
    log_info(f"正在打包压缩至: {output_zip_path}")
    total_files = sum(1 for _ in source_dir.rglob("*") if _.is_file())
    count = 0
    with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in source_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(source_dir)
                zf.write(file, arcname)
                count += 1
                if count % 50 == 0 or count == total_files:
                    print(f"\r压缩进度: {count}/{total_files} 文件...", end="", flush=True)
    print()
    size_mb = output_zip_path.stat().st_size / (1024 * 1024)
    log_info(f"压缩完成！压缩包大小: {size_mb:.2f} MB")


def copy_project_assets_and_scripts(target_dir: Path, version: str):
    """复制最新流水线资源、模型、配置与 Python 脚本到目标目录"""
    # 1. 确保 OCR 模型就绪
    from configure import configure_ocr_model
    configure_ocr_model()

    # 2. 复制 resource
    target_res = target_dir / "resource"
    if target_res.exists():
        shutil.rmtree(target_res, ignore_errors=True)
    shutil.copytree(
        ASSETS_DIR / "resource",
        target_res,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git*"),
        dirs_exist_ok=True,
    )

    # 3. 复制并更新 interface.json
    target_interface = target_dir / "interface.json"
    interface_data = load_jsonc_file(ASSETS_DIR / "interface.json")
    interface_data["version"] = version.lstrip("v")
    with open(target_interface, "w", encoding="utf-8") as f:
        json.dump(interface_data, f, ensure_ascii=False, indent=4)

    # 4. 复制 agent
    target_agent = target_dir / "agent"
    if target_agent.exists():
        shutil.rmtree(target_agent, ignore_errors=True)
    shutil.copytree(
        ROOT_DIR / "agent",
        target_agent,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.log"),
        dirs_exist_ok=True,
    )

    # 5. 复制根目录关键脚本与文档
    for file_name in ["game_input.py", "run_tdm.py", "README.md", "LICENSE"]:
        src_file = ROOT_DIR / file_name
        if src_file.exists():
            shutil.copy2(src_file, target_dir)

    # 6. 生成启动脚本
    create_launcher_scripts(target_dir)


def build_fast_local(version: str, os_name: str, arch: str, make_zip: bool = True) -> Path:
    """基于本地已有 gui/ 目录进行极速增量打包"""
    log_step(f"开始极速本地打包 [{version}] ({os_name}-{arch})")

    if not GUI_DIR.exists() or not (GUI_DIR / "MFAAvalonia.exe").exists():
        raise RuntimeError("未检测到本地 gui/ 目录或缺少 MFAAvalonia.exe！请先运行 Clean 构建或从 Release 准备 gui 环境。")

    output_dir_name = f"MAAACOL-{version}-{os_name}-{arch}"
    target_dir = DIST_DIR / output_dir_name

    log_info(f"清理旧的输出目录: {target_dir}")
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    log_info("正在复制本地 UI 前端与框架运行时组件...")
    # 忽略脏数据、调试图、缓存等
    ignore_patterns = shutil.ignore_patterns(
        "debug", "logs", "temp", "backup",
        "__pycache__", "*.pyc", "*.log",
        "resource", "agent", "interface.json",  # 后面会使用最新版覆盖
        "game_input.py"
    )

    for item in GUI_DIR.iterdir():
        if item.name in ["debug", "logs", "temp", "backup", "__pycache__"]:
            continue
        dest = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=ignore_patterns, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    log_info("正在同步最新的项目资源与脚本...")
    copy_project_assets_and_scripts(target_dir, version)

    log_info(f"构建目录准备完毕: {target_dir}")

    if make_zip:
        zip_path = DIST_DIR / f"{output_dir_name}.zip"
        zip_directory(target_dir, zip_path)
        return zip_path
    return target_dir


def sync_to_gui(version: str):
    """仅同步最新代码和资源到开发测试用的 gui/ 目录"""
    log_step("同步资源到本地 gui/ 目录")
    if not GUI_DIR.exists():
        log_error("本地 gui/ 目录不存在！")
        return

    copy_project_assets_and_scripts(GUI_DIR, version)

    # 清理 gui 下旧的 debug 截图避免占用空间
    for clean_folder in ["debug", "temp"]:
        folder = GUI_DIR / clean_folder
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            folder.mkdir(exist_ok=True)

    log_info("最新资源和脚本已同步至 gui/ 目录，可直接运行测试！")


def download_github_release(repo: str, keyword: str, dest_dir: Path, proxy: str = "") -> Path:
    """自动从 GitHub Releases 下载匹配的文件"""
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    log_info(f"正在查询 {repo} 最新版本...")
    headers = {"User-Agent": "MAAACOL-Builder"}
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        release_data = json.loads(resp.read().decode("utf-8"))

    tag_name = release_data.get("tag_name", "latest")
    log_info(f"找到版本: {tag_name}")

    matched_asset = None
    for asset in release_data.get("assets", []):
        name = asset.get("name", "")
        if keyword in name:
            matched_asset = asset
            break

    if not matched_asset:
        raise RuntimeError(f"在 {repo} 中未找到包含 '{keyword}' 的构建产物！")

    download_url = matched_asset["browser_download_url"]
    file_name = matched_asset["name"]
    dest_file = dest_dir / file_name

    if proxy:
        if not proxy.endswith("/"):
            proxy += "/"
        download_url = proxy + download_url

    log_info(f"开始下载: {file_name}")
    log_info(f"下载地址: {download_url}")

    # 下载带进度展示
    def report_progress(block_num, block_size, total_size):
        if total_size > 0:
            percent = (block_num * block_size / total_size) * 100
            downloaded_mb = (block_num * block_size) / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(f"\r下载进度: {min(100.0, percent):.1f}% ({downloaded_mb:.1f}MB/{total_mb:.1f}MB)", end="", flush=True)

    urllib.request.urlretrieve(download_url, dest_file, reporthook=report_progress)
    print()
    log_info(f"下载完成: {dest_file}")
    return dest_file


def build_clean(version: str, os_name: str, arch: str, proxy: str = "", make_zip: bool = True) -> Path:
    """干净构建：下载核心运行依赖后通过 install.py 组装"""
    log_step(f"开始全新干净构建 [{version}] ({os_name}-{arch})")

    cache_dir = ROOT_DIR / ".cache"
    cache_dir.mkdir(exist_ok=True)
    deps_dir = ROOT_DIR / "deps"
    deps_dir.mkdir(exist_ok=True)
    mfa_dir = ROOT_DIR / "MFA"
    mfa_dir.mkdir(exist_ok=True)
    install_dir = ROOT_DIR / "install"
    if install_dir.exists():
        shutil.rmtree(install_dir, ignore_errors=True)
    install_dir.mkdir(exist_ok=True)

    # 1. 检查或下载 MaaFramework
    if not (deps_dir / "bin").exists():
        log_info("正在准备 MaaFramework 运行时...")
        maa_keyword = f"MAA-{os_name}-{arch}"
        zip_file = download_github_release("MaaXYZ/MaaFramework", maa_keyword, cache_dir, proxy=proxy)
        log_info(f"解压 MaaFramework 到 {deps_dir} ...")
        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(deps_dir)

    # 2. 检查或下载 MFAAvalonia (桌面平台)
    if os_name != "android":
        mfa_plat = "win" if os_name == "win" else ("osx" if os_name == "macos" else "linux")
        mfa_arch = "x64" if arch == "x86_64" else "arm64"
        mfa_keyword = f"-{mfa_plat}-{mfa_arch}"
        if not (mfa_dir / "MFAAvalonia.exe").exists() and not (mfa_dir / "MFAAvalonia.dll").exists():
            log_info("正在准备 MFAAvalonia 前端...")
            zip_file = download_github_release("SweetSmellFox/MFAAvalonia", mfa_keyword, cache_dir, proxy=proxy)
            log_info(f"解压 MFAAvalonia 到 {mfa_dir} ...")
            with zipfile.ZipFile(zip_file, "r") as zf:
                zf.extractall(mfa_dir)

        # 清除自带运行时
        if (mfa_dir / "runtimes").exists():
            shutil.rmtree(mfa_dir / "runtimes", ignore_errors=True)

        log_info("复制 MFA 文件至 install ...")
        shutil.copytree(mfa_dir, install_dir, dirs_exist_ok=True)

    # 3. 运行 install.py
    log_info("执行 tools/install.py ...")
    cmd = [sys.executable, str(TOOLS_DIR / "install.py"), version, os_name, arch]
    subprocess.check_call(cmd, cwd=TOOLS_DIR)

    # 4. 生成双击运行脚本
    create_launcher_scripts(install_dir)

    # 5. 转移到 dist 目录
    output_dir_name = f"MAAACOL-{version}-{os_name}-{arch}"
    target_dir = DIST_DIR / output_dir_name
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    shutil.copytree(install_dir, target_dir, dirs_exist_ok=True)

    if make_zip:
        zip_path = DIST_DIR / f"{output_dir_name}.zip"
        zip_directory(target_dir, zip_path)
        return zip_path
    return target_dir


def main():
    parser = argparse.ArgumentParser(description="MAAACOL 本地打包构建工具")
    parser.add_argument("--mode", choices=["local", "clean", "sync-gui"], default="local",
                        help="构建模式: local (本地极速打包), clean (干净全量打包), sync-gui (同步到开发gui目录)")
    parser.add_argument("--version", default="", help="打包版本号 (默认自动读取 interface.json)")
    parser.add_argument("--os", default="", help="目标系统: win, macos, linux, android")
    parser.add_argument("--arch", default="", help="架构: x86_64, aarch64")
    parser.add_argument("--proxy", default="", help="GitHub 下载镜像加速前缀 (如 https://ghproxy.net/)")
    parser.add_argument("--no-zip", action="store_true", help="不生成 zip 压缩包，只保留目录")
    parser.add_argument("--open-dir", action="store_true", help="构建完成后打开 dist 目录")

    args = parser.parse_args()

    default_os, default_arch = detect_system()
    os_name = args.os or default_os
    arch = args.arch or default_arch
    version = args.version or get_current_version()

    DIST_DIR.mkdir(exist_ok=True)

    start_time = time.time()
    result_path = None

    try:
        if args.mode == "sync-gui":
            sync_to_gui(version)
            return

        if args.mode == "local":
            result_path = build_fast_local(version, os_name, arch, make_zip=not args.no_zip)
        elif args.mode == "clean":
            result_path = build_clean(version, os_name, arch, proxy=args.proxy, make_zip=not args.no_zip)

        elapsed = time.time() - start_time
        log_step(f"打包构建完成！(耗时 {elapsed:.2f} 秒)")
        if result_path:
            log_info(f"最终输出路径: {result_path}")
            if args.open_dir:
                try:
                    if platform.system() == "Windows":
                        os.startfile(str(DIST_DIR))
                    elif platform.system() == "Darwin":
                        subprocess.run(["open", str(DIST_DIR)])
                    else:
                        subprocess.run(["xdg-open", str(DIST_DIR)])
                except Exception:
                    pass

    except Exception as e:
        log_error(f"打包构建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
内嵌 .NET 运行时组装模块

上游 MFAAvalonia 产物属于框架依赖发布：包内既没有 .NET 运行时，也未保留其依赖安装脚本，
在未安装 .NET 运行时的主机上 MAAACOL.exe 会直接启动失败。这里把官方 dotnet-runtime 放进包内
runtime/，由 start_gui.bat 设置 DOTNET_ROOT，使 GUI 不依赖主机 .NET 环境。
同时把 VC++ 运行库复制到原生库所在目录，避免主机缺少 VC++ Redistributable 时原生库加载失败。
"""

import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

# aka.ms 会重定向到当前最新的 10.0.x 运行时包（应用 runtimeconfig 要求 Microsoft.NETCore.App 10.0.0）
DOTNET_RUNTIME_URL = "https://aka.ms/dotnet/10.0/dotnet-runtime-win-x64.zip"
# MaaFramework / onnxruntime / opencv 原生库依赖的 VC++ 2015-2022 运行库（属于允许随应用分发的 Redistributable）
VC_RUNTIME_DLLS = [
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_codecvt_ids.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "concrt140.dll",
]
# 原生库实际所在目录：GUI（runtimes/win-x64/native）与便携 Python（maafw 包的 maa/bin）各有一份
VC_RUNTIME_TARGETS = ["runtimes/win-x64/native", "python/Lib/site-packages/maa/bin"]
MARKER_NAME = ".maaacol-dotnet"


def _download(url: str, dest: Path):
    print(f"[INFO] 正在下载 .NET 运行时: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "MAAACOL-Builder"})
    with urllib.request.urlopen(request) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    print(f"[INFO] 下载完成: {dest}")


def build_embedded_dotnet(cache_dir: Path) -> Path:
    """在缓存目录内解压官方 dotnet-runtime，返回解压根目录（含 host/ 与 shared/）"""
    runtime_dir = cache_dir / "runtime"
    # shortcut: 缓存仅按 URL 复用，需要更新运行时补丁版本时删除 .cache/embedded-dotnet
    if (runtime_dir / MARKER_NAME).exists():
        return runtime_dir

    cache_dir.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(runtime_dir, ignore_errors=True)
    runtime_dir.mkdir(parents=True)

    zip_path = cache_dir / Path(DOTNET_RUNTIME_URL).name
    if not zip_path.exists():
        _download(DOTNET_RUNTIME_URL, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(runtime_dir)
    (runtime_dir / MARKER_NAME).write_text(DOTNET_RUNTIME_URL, encoding="ascii")
    return runtime_dir


def install_embedded_dotnet(target_dir: Path, cache_dir: Path) -> bool:
    """把 .NET 运行时复制进发布包（target_dir/runtime），失败返回 False 由调用方回退主机 .NET"""
    # shortcut: 只处理 Windows x64 产物，其余平台仍为框架依赖
    if sys.platform != "win32":
        return False
    try:
        runtime_dir = build_embedded_dotnet(cache_dir)
        dest = target_dir / "runtime"
        if (dest / MARKER_NAME).exists():
            return True
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(runtime_dir, dest)
        return True
    except Exception as e:  # 网络/权限异常不应中断打包，回退为主机 .NET 运行时
        print(f"[WARN] .NET 运行时组装失败：{e}")
        return False


def install_vc_runtime(target_dir: Path) -> bool:
    """把 VC++ 运行库复制到原生库同级目录（该目录优先于系统搜索路径），失败仅告警"""
    if sys.platform != "win32":
        return False
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    copied = 0
    for rel_dir in VC_RUNTIME_TARGETS:
        dest_dir = target_dir / rel_dir
        if not dest_dir.is_dir():
            continue
        for name in VC_RUNTIME_DLLS:
            src = system32 / name
            if src.exists():
                shutil.copy2(src, dest_dir / name)
                copied += 1
    if copied:
        print(f"[INFO] 已随包附带 VC++ 运行库 {copied} 个文件")
    else:
        print("[WARN] 未找到 VC++ 运行库，主机需自行安装 VC++ Redistributable")
    return copied > 0

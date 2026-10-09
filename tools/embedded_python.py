"""
便携 Python 组装模块

发布包内自带 python/ 目录（官方 embeddable Python + requirements 依赖），
使 GUI 的 Agent 插件与 CLI runner 完全不依赖主机 Python 环境。
"""

import hashlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

EMBED_PY_VERSION = "3.12.8"
EMBED_PY_URL = (
    f"https://www.python.org/ftp/python/{EMBED_PY_VERSION}"
    f"/python-{EMBED_PY_VERSION}-embed-amd64.zip"
)
# 记录（Python 版本 + requirements 内容）哈希，用于判断已就绪的便携环境是否需要重建
MARKER_NAME = ".maaacol-env"


def _cache_digest(requirements: Path) -> str:
    raw = requirements.read_bytes()
    return f"{EMBED_PY_VERSION} {hashlib.sha256(raw).hexdigest()}"


def _is_ready(python_dir: Path, digest: str) -> bool:
    marker = python_dir / MARKER_NAME
    try:
        return (python_dir / "python.exe").exists() and marker.read_text(encoding="ascii").strip() == digest
    except OSError:
        return False


def _write_pth(python_dir: Path):
    """embeddable 包默认隔离 sys.path，需把 site-packages 写进 ._pth 才能 import maa"""
    for pth in python_dir.glob("python*._pth"):
        pth.write_text(f"{pth.stem}.zip\n.\nLib\\site-packages\nimport site\n", encoding="ascii", newline="\r\n")


def _download(url: str, dest: Path):
    print(f"[INFO] 正在下载便携 Python: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "MAAACOL-Builder"})
    with urllib.request.urlopen(request) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    print(f"[INFO] 下载完成: {dest}")


def build_embedded_python(cache_dir: Path, requirements: Path) -> Path:
    """在缓存目录内构建（或复用）便携 Python 环境，返回其 python 目录"""
    digest = _cache_digest(requirements)
    python_dir = cache_dir / "python"
    if _is_ready(python_dir, digest):
        return python_dir

    cache_dir.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(python_dir, ignore_errors=True)
    python_dir.mkdir(parents=True)

    zip_path = cache_dir / Path(EMBED_PY_URL).name
    if not zip_path.exists():
        _download(EMBED_PY_URL, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(python_dir)
    _write_pth(python_dir)

    site_packages = python_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    print("[INFO] 正在向便携 Python 安装依赖，请稍候...")
    # --python-version/--implementation/--only-binary 让 pip 按便携解释器版本解析 wheel：
    # 构建机解释器与便携 Python 版本不同时（如 CI runner 为 3.13），否则会装进 cp313 的 numpy
    target_python = ".".join(EMBED_PY_VERSION.split(".")[:2])
    subprocess.check_call(
        [
            sys.executable, "-m", "pip", "install",
            "--disable-pip-version-check", "--no-input", "--no-warn-script-location",
            "--only-binary=:all:",
            "--python-version", target_python,
            "--implementation", "cp",
            "--target", str(site_packages),
            "-r", str(requirements),
        ]
    )
    (python_dir / MARKER_NAME).write_text(digest, encoding="ascii")
    return python_dir


def install_embedded_python(
    target_dir: Path, cache_dir: Path, requirements: Path, target_arch: str = "x86_64"
) -> bool:
    """把便携 Python 复制进发布包（target_dir/python），失败返回 False 由调用方回退主机 Python"""
    # shortcut: 便携 Python 基于 python.org 的 Windows embeddable 包，只能在 Windows 构建机上组装，
    # 且官方 embeddable 仅提供 amd64 版本；win-aarch64 产物装入 amd64 解释器会与 ARM64 原生库平台不符，
    # 非 Windows 构建机继续组装会把 Windows 解释器与错误平台的 maafw wheel 装进产物，因此一并跳过
    if sys.platform != "win32" or target_arch != "x86_64":
        print("[WARN] 便携 Python 仅支持 Windows x86_64 产物组装，跳过（Agent 将回退主机 python）")
        return False
    try:
        python_dir = build_embedded_python(cache_dir, requirements)
        dest = target_dir / "python"
        if _is_ready(dest, _cache_digest(requirements)):
            return True
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(python_dir, dest)
        return True
    except Exception as e:  # 网络/权限异常时不应中断打包，回退为主机 Python
        print(f"[WARN] 便携 Python 组装失败：{e}")
        return False


# 与 Agent 协议版本强相关、必须两侧同源的原生库
AGENT_NATIVE_DLLS = ["MaaFramework.dll", "MaaAgentClient.dll", "MaaAgentServer.dll", "MaaUtils.dll"]


def verify_agent_env(target_dir: Path) -> None:
    """校验发布包内 Agent 运行环境，不通过直接抛异常，避免打出“能装不能跑”的包"""
    probe = subprocess.run(
        [str(target_dir / "python" / "python.exe"), "-c", "import maa.agent.agent_server"],
        capture_output=True,
    )
    if probe.returncode != 0:
        raise RuntimeError(
            f"包内 Python 无法导入 maa.agent：{probe.stderr.decode('utf-8', 'replace').strip()[:200]}"
        )

    # 便携 Python 版本固定，依赖 wheel 的 ABI 必须匹配，否则装得进去但 import 不了
    expected_tag = "cp" + "".join(EMBED_PY_VERSION.split(".")[:2])
    for dist_info in (target_dir / "python" / "Lib" / "site-packages").glob("*.dist-info"):
        wheel_meta = dist_info / "WHEEL"
        if not wheel_meta.exists():
            continue
        for line in wheel_meta.read_text(encoding="utf-8").splitlines():
            if not line.startswith("Tag:"):
                continue
            interpreter_tag = line.split(":", 1)[1].strip().split("-")[0]
            if interpreter_tag.startswith("cp") and interpreter_tag != expected_tag:
                raise RuntimeError(
                    f"{dist_info.name} 的 wheel 标签为 {interpreter_tag}，与便携 Python {EMBED_PY_VERSION}"
                    f"（应为 {expected_tag}）不匹配，包内依赖将无法导入。"
                )

    # 原生运行时(AgentClient)必须与便携 Python 的绑定(AgentServer)出自同一版本：
    # 协议版本漂移时 Agent 会以 "Protocol version mismatch" 退出（GUI 表现：Agent 启动失败）
    maa_bin = target_dir / "python" / "Lib" / "site-packages" / "maa" / "bin"
    native_dir = next(target_dir.glob("runtimes/*/native"), None)
    if not native_dir or not maa_bin.exists():
        return
    for native_name in AGENT_NATIVE_DLLS:
        native_file, binding_file = native_dir / native_name, maa_bin / native_name
        if native_file.exists() and binding_file.exists() and native_file.read_bytes() != binding_file.read_bytes():
            raise RuntimeError(
                f"{native_name} 在 runtimes/ 与便携 Python 中版本不一致，Agent 将因协议版本不匹配启动失败。"
                "请执行 Clean 构建，或用 Setup gui/ Environment 刷新 gui/ 运行时。"
            )

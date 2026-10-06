"""GUIDE Phần 1 - Dựng tác tử (agent) bằng Deep Agents.   >>> SINH VIÊN CÀI ĐẶT make_backend VÀ build_agent <<<

Pseudo-code: guides/pseudocode/01_agent.md
Kiểm tra:    pytest tests/test_02_agent.py
"""
import atexit
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from deepagents.backends.protocol import ExecuteResponse

from .model import make_model
from .subagents import get_subagents

# ---- CÓ SẴN, KHÔNG SỬA: system prompt dùng chung cho mọi sinh viên (để đường cơ sở so sánh được) ----
PATHS_NOTE = (
    "PATHS: every path is relative to the sandbox root and never starts with '/'. "
    "The task files are in the folder workspace/ (for example workspace/app.log). "
    "Use exactly this relative form both in the file tools and in the shell (execute); "
    "the shell starts in the sandbox root. "
)
BASE_PROMPT = (
    "You are an engineering assistant working in a sandbox. "
    + PATHS_NOTE
    + "Use the shell to run Python and tests. "
    "When you are done, reply with a short summary that mentions only files you really created or changed."
)
SKILLS_NOTE = (
    " Skills are in the folder skills/ (one sub-folder per skill with a SKILL.md). "
    "As your FIRST action, read the SKILL.md of every skill whose description could apply to the task, "
    "then follow them. Never modify skills/."
)
SUBAGENTS_NOTE = (
    " You have specialised subagents (see the description of the task tool). "
    "For anything beyond a trivial step, delegate to a suitable subagent and put ALL the task rules and file paths "
    "in the delegation message, because a subagent sees only what you send. "
    "Check what a subagent returns before you rely on it."
)
# --------------------------------------------------------------------------------------------------


def _find_posix_shell() -> str | None:
    """On Windows, locate a POSIX shell (Git Bash). WSL's System32 bash.exe is skipped (it is another machine)."""
    candidates = [shutil.which("bash"), shutil.which("sh")]
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
        if root:
            candidates += [str(Path(root) / "Git" / "bin" / "bash.exe"), str(Path(root) / "Programs" / "Git" / "bin" / "bash.exe")]
    for c in candidates:
        if c and Path(c).exists() and "system32" not in c.lower():
            return c
    return None


class _LabBackend(LocalShellBackend):
    """LocalShellBackend that runs commands with a POSIX shell also on Windows (the lab assumes /bin/sh)."""

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        shell = _find_posix_shell() if sys.platform == "win32" else None
        if shell is None:
            return super().execute(command, timeout=timeout)
        limit = timeout if timeout is not None else self._default_timeout
        try:
            r = subprocess.run(
                [shell, "-c", command], check=False, capture_output=True, stdin=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", timeout=limit, env=self._env, cwd=str(self.cwd),
            )
        except subprocess.TimeoutExpired:
            return ExecuteResponse(output=f"Error: command timed out after {limit} seconds.", exit_code=124, truncated=False)
        parts = []
        if r.stdout:
            parts.append(r.stdout)
        if r.stderr:
            parts.extend(f"[stderr] {line}" for line in r.stderr.strip().split("\n"))
        output = "\n".join(parts) if parts else "<no output>"
        truncated = len(output) > self._max_output_bytes
        if truncated:
            output = output[: self._max_output_bytes] + f"\n\n... Output truncated at {self._max_output_bytes} bytes."
        if r.returncode != 0:
            output = f"{output.rstrip()}\n\nExit code: {r.returncode}"
        return ExecuteResponse(output=output, exit_code=r.returncode, truncated=truncated)


def _python_shims() -> str:
    """Folder (outside the repo and the sandbox) with `python` and `python3` launchers.

    The agent's PATH then names a temp folder instead of the repo's .venv, so the shell does not reveal where the
    lab (tasks/, the checkers) lives on disk.
    """
    d = tempfile.mkdtemp(prefix="lab-bin-")
    atexit.register(shutil.rmtree, d, ignore_errors=True)
    target = Path(sys.executable).as_posix()
    for name in ("python", "python3"):
        f = Path(d) / name
        f.write_bytes(f'#!/bin/sh\nexec "{target}" "$@"\n'.encode("utf-8"))
        f.chmod(0o755)
    return d


def make_backend(sandbox: Path):
    """Tạo backend (môi trường thực thi) cho tác tử.

    Yêu cầu:
      - Thư mục gốc (root_dir) là `sandbox`; đường dẫn tương đối `workspace/...` và `skills/...`
        phải dùng được ở CẢ công cụ tệp lẫn shell (shell chạy với thư mục làm việc = `sandbox`).
      - Tác tử chạy được lệnh shell và gọi được `python` (cần đặt PATH).
      - KHÔNG chuyển biến môi trường của bạn vào shell của tác tử (khóa API không được lộ).
    """
    bin_dir = _python_shims()
    if sys.platform == "win32":
        extra = [r"C:\Program Files\Git\usr\bin", r"C:\Program Files\Git\bin"]
        shell = _find_posix_shell()
        if shell:
            extra[:0] = [str(Path(shell).parent), str(Path(shell).parent.parent / "usr" / "bin")]
        env = {
            "PATH": os.pathsep.join([bin_dir, *extra]),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
            "TEMP": os.environ.get("TEMP", str(sandbox)),
            "TMP": os.environ.get("TMP", str(sandbox)),
        }
    else:
        env = {"PATH": bin_dir + ":/usr/local/bin:/usr/bin:/bin"}
    env.update({"HOME": str(sandbox), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"})
    return _LabBackend(root_dir=sandbox, virtual_mode=True, inherit_env=False, env=env, timeout=120)


def build_agent(sandbox: Path, mode: str = "single", use_skills: bool = False, model=None):
    """Tạo tác tử Deep Agents.

    Tham số:
      sandbox:    thư mục chứa `workspace/` (và `skills/` nếu có).
      mode:       "single"    -> tác tử mặc định (có subagent `general-purpose` sẵn của Deep Agents)
                  "subagents" -> thêm các subagent từ `get_subagents()` (nối PATHS_NOTE vào `system_prompt` của MỖI subagent,
                                 vì subagent không nhận BASE_PROMPT) và thêm SUBAGENTS_NOTE vào prompt chính
      use_skills: True -> nạp thư mục "/skills/" qua tham số `skills=` của create_deep_agent
                  và thêm SKILLS_NOTE vào prompt.
      model:      mô hình ngôn ngữ; None -> dùng `make_model()`.
    mode không hợp lệ -> ném ValueError.
    Trả về: đồ thị (graph) đã biên dịch, gọi bằng `.invoke({"messages": [...]})`.
    """
    if mode not in ("single", "subagents"):
        raise ValueError(f"unknown mode: {mode!r} (expected 'single' or 'subagents')")
    kwargs = {}
    prompt = BASE_PROMPT
    if mode == "subagents":
        kwargs["subagents"] = [{**sub, "system_prompt": sub["system_prompt"] + " " + PATHS_NOTE} for sub in get_subagents()]
        prompt = prompt + SUBAGENTS_NOTE
    if use_skills:
        kwargs["skills"] = ["/skills/"]
        prompt = prompt + SKILLS_NOTE
    return create_deep_agent(
        model=model or make_model(),
        system_prompt=prompt,
        backend=make_backend(sandbox),
        **kwargs,
    )

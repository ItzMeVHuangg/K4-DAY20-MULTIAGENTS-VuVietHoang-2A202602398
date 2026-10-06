"""GUIDE Phần 3 - Người tuyển chọn skill (skill curator): tự viết skill từ các lần chạy thất bại.   >>> SINH VIÊN CÀI ĐẶT curate_skills <<<

Pseudo-code: guides/pseudocode/04_curator.md
Kiểm tra:    pytest tests/test_04_curator.py
Chạy thật:   python -m lab.curator
"""
import json
import re
from pathlib import Path

from .tasks import ROOT, eval_markers   # có sẵn: gốc của lab; định danh của tác vụ đánh giá, tính lúc chạy

TRACE_CHARS = 6000
PROMPT = """You write SKILLS for a coding and data-analysis agent.
Below are the failed checks (name and the feedback of the review bot) and the end of the trace of each run.
Find general PROCESS mistakes (not specific answers) and write at most {max_skills} short skills that help the agent avoid
these mistakes on a NEW task of the same kind.

Rules:
- A skill must be general: no task ids, no file names that belong to one task, no answers, no numbers from the data.
  Names required by a convention rule (for example an output file name or a JSON key that a rule demands) are allowed.
- The failed checks named `rule_*` are conventions of the organisation that the agent CANNOT guess because the task
  statement does not mention them. State each such rule explicitly and exactly as an imperative checklist item, with its
  concrete format (heading text, header order, key names, units, sort order, naming pattern), taken from the feedback.
  Vague advice such as "follow all conventions" is useless; the agent must be able to apply each item literally.
- Group the rules by kind of task (for example: code fixing, tabular data analysis, log analysis) and tell the agent
  when each group applies. Add one line telling the agent to re-read the checklist before it finishes.
- A failed check that is not a `rule_*` check (for example one about not modifying existing files) is also a rule: state it.
- Each skill has YAML frontmatter with `name` (lower case, dashes) and `description` (one sentence starting with
  "Use when ..." and naming a broad kind of task), then at most 40 lines of imperative instructions (a numbered checklist works best).
- Output format, character for character:
=== SKILL: <name> ===
---
name: <name>
description: <when to use it>
---
<content>
=== END ===

{runs}
"""

# ---- CÓ SẴN, KHÔNG SỬA: kiểm tra và tách khối skill (phần dễ sai và liên quan bảo mật) ----------------
SAFE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_skill(text: str, expected_name: str | None = None) -> list[str]:
    """Kiểm tra nội dung một SKILL.md. Trả về danh sách vấn đề (rỗng = hợp lệ).

    Quy tắc: có khối YAML frontmatter; `name` chữ thường/số/gạch ngang (tối đa 64 ký tự) và bằng `expected_name`
    nếu được truyền; có `description` (tối đa 1024 ký tự); phần thân tối đa 80 dòng; không chứa chuỗi nào của
    `eval_markers()`. Quy tắc về `name` cũng là biện pháp bảo mật: tên khối do LLM sinh ra được dùng để tạo
    đường dẫn, nên `../evil` không được lọt qua.
    """
    problems = []
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text.strip() + "\n", re.S)
    if not m:
        return ["missing YAML frontmatter"]
    front, body = m.groups()
    name = re.search(r"^name:\s*(.+)$", front, re.M)
    desc = re.search(r"^description:\s*(.+)$", front, re.M)
    n = name.group(1).strip() if name else ""
    if not SAFE_NAME.fullmatch(n) or len(n) > 64:
        problems.append("invalid name")
    elif expected_name is not None and n != expected_name:
        problems.append("name differs from the block name")
    if not desc or len(desc.group(1).strip()) > 1024:
        problems.append("missing or too long description")
    if len(body.strip().splitlines()) > 80:
        problems.append("body longer than 80 lines")
    low = text.lower()
    for marker in eval_markers():
        if marker in low:
            problems.append(f"mentions evaluation material: {marker}")
    return problems


def parse_skill_blocks(reply: str) -> list[tuple[str, str]]:
    """Tách câu trả lời của LLM thành danh sách (name, nội dung SKILL.md).

    Khuôn dạng: `=== SKILL: <name> ===` ... `=== END ===`. Một khối kết thúc ở điểm nào đến trước trong ba điểm:
    `=== END ===`, tiêu đề `=== SKILL:` kế tiếp, hoặc cuối văn bản (LLM đôi khi quên dòng END).
    """
    pattern = re.compile(r"^=== SKILL: (\S+) ===[ \t]*\n(.*?)(?=^=== END ===|^=== SKILL: |\Z)", re.S | re.M)
    return [(name, text.strip()) for name, text in pattern.findall(str(reply))]
# --------------------------------------------------------------------------------------------------


def curate_skills(results_dir="results", source_condition="baseline", out_dir=None, model=None, max_skills: int = 3) -> list[Path]:
    """Đọc các lần chạy của TÁC VỤ HỌC (role == "learn") trong `source_condition`, nhờ LLM viết skill, ghi file.

    Các bước: nạp run.json + trace.md -> (nếu không có check nào thất bại: in cảnh báo và trả về [] mà KHÔNG gọi LLM)
    -> dựng prompt -> model.invoke(prompt) -> parse_skill_blocks -> validate_skill(text, expected_name=name)
    -> ghi `<out_dir>/<name>/SKILL.md`. Mặc định `out_dir` = <gốc lab>/skills/auto (dùng `ROOT` từ lab.tasks).
    Giữ tối đa `max_skills` skill hợp lệ; skill không hợp lệ bị bỏ qua.
    Prompt chứa, với mỗi check thất bại, TÊN và trường `detail` (lời nhận xét của bot đánh giá: phát biểu quy tắc bị vi phạm)
    cùng phần cuối của vết (trace). Với tác vụ học, `detail` chỉ phát biểu quy tắc, không chứa đáp án.
    Tuyệt đối KHÔNG đưa dữ liệu của tác vụ đánh giá (role == "eval") vào prompt.
    model mặc định: make_model() (lab.model).
    Trả về: danh sách đường dẫn SKILL.md đã ghi.
    """
    results_dir = Path(results_dir)
    out_dir = Path(out_dir) if out_dir is not None else ROOT / "skills" / "auto"

    runs = []
    for run_json in sorted((results_dir / source_condition).glob("*/run.json")):
        r = json.loads(run_json.read_text(encoding="utf-8"))
        if r.get("role") != "learn":      # never use evaluation-task data
            continue
        trace_file = run_json.parent / "trace.md"
        trace = trace_file.read_text(encoding="utf-8")[-TRACE_CHARS:] if trace_file.exists() else ""
        failed = [(c.get("name", ""), c.get("detail", "")) for c in r.get("checks", []) if not c.get("passed")]
        runs.append({"task": r.get("task", run_json.parent.name), "failed": failed, "trace": trace})

    if not any(r["failed"] for r in runs):
        print("WARNING: no failed check in the learning tasks - nothing to learn from, no skill written.")
        return []

    blocks = []
    for r in runs:
        if not r["failed"]:
            continue
        failed_txt = "\n".join(f"- {name}: {detail}" for name, detail in r["failed"])
        blocks.append(f"## Run: {r['task']}\nFailed checks (name: reviewer feedback):\n{failed_txt}\n\nEnd of the trace:\n{r['trace']}")
    prompt = PROMPT.format(max_skills=max_skills, runs="\n\n".join(blocks))

    if model is None:
        from .model import make_model
        model = make_model()
    reply = model.invoke(prompt).content
    if isinstance(reply, list):       # some providers return a list of content parts
        reply = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in reply)

    written = []
    for name, text in parse_skill_blocks(reply):
        if len(written) >= max_skills:
            break
        problems = validate_skill(text, expected_name=name)
        if problems:
            print(f"skipped skill {name!r}: {'; '.join(problems)}")
            continue
        path = out_dir / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    for p in curate_skills():
        print("wrote", p)

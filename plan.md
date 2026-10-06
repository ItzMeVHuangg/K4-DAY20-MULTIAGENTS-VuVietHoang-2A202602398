# Plan thực hiện lab (theo GUIDE.md)

> Ghi chú cấu hình: dùng Gemini qua LangChain `init_chat_model` (không set đủ 3 biến `AZURE_OPENAI_*`):
> `.env`: `LAB_MODEL=google_genai:gemini-2.0-flash`, `GOOGLE_API_KEY=<key>`; cài thêm `pip install langchain-google-genai`.

## Phần 0. Cài đặt và làm quen

- [X] [run] Tạo venv, `pip install -e .`
- [x] [code] Cài thêm `langchain-google-genai`, sửa `.env` dùng `LAB_MODEL=google_genai:gemini-...` + `GOOGLE_API_KEY`
- [X] [run] `cp .env.example .env` rồi điền biến Gemini, `mkdir -p report && cp REPORT_TEMPLATE.md report/REPORT.md`
- [X] [run] `pytest tests/test_01_provided.py` → kỳ vọng `12 passed`
- [x] [run] Kiểm tra kết nối model: `python -c "from lab.model import make_model; print(make_model().invoke('Reply with OK').content)"`
- [x] [run] `python scripts/tour.py` (không tốn token)
- [x] [report] Điền mục 3 của `report/REPORT.md`: công cụ mặc định, mô tả subagent `general-purpose`, trích câu từ mô tả `task` và `execute`

## Phần 1. Hoàn thiện harness với Deep Agents

- [x] [code] Cài `src/lab/subagents.py` theo `guides/pseudocode/02_subagents.md`
- [x] [run] `pytest tests/test_02_agent.py -k subagents`
- [x] [code] Cài `src/lab/agent.py` (`make_backend`, `build_agent`) theo `01_agent.md`
- [x] [run] `pytest tests/test_02_agent.py` (toàn bộ)
- [x] [code] Cài `src/lab/runner.py` (`run_task`) theo `03_runner.md`
- [x] [run] `pytest tests/test_03_runner.py`
- [x] [run] Chạy thật: `python -m lab.runner --condition baseline --tasks data-learn` (tính là baseline của data-learn, không chạy lại ở Phần 2)
- [x] [fix bug] Kiểm tra `results/baseline/data-learn/run.json` và `trace.md` tồn tại hợp lệ; nếu lỗi, xem mục "Xử lý sự cố" cuối GUIDE.md

## Phần 2. Chạy tác vụ học, đo đạc, phân loại lỗi

- [x] [run] `python -m lab.runner --condition baseline --tasks code-learn logs-learn`
- [x] [run] `python -m lab.runner --condition subagents --tasks learn`
- [x] [report] Phân loại lỗi (nhóm A-G) cho 3 tác vụ học vào mục 4 báo cáo, có bằng chứng trích từ `detail`/vết
- [x] [run] `python scripts/check_breakdown.py` làm bằng chứng phủ định nếu lỗi tập trung nhóm E
- [x] [report] Điền mục 5 báo cáo: `subagent_calls`, nội dung giao việc, so sánh token với baseline

## Phần 3. Self-evolving: curator tự viết skill

- [x] [code] Cài `curate_skills` trong `src/lab/curator.py` theo `04_curator.md` và `05_skill_quality.md`
- [x] [run] `pytest tests/test_04_curator.py`
- [x] [run] `python -m lab.curator`
- [x] [report] Đánh giá từng skill sinh ra (mục 6): tổng quát hay riêng tác vụ học, đúng/sai, độ dài & description
- [x] [fix bug] Nếu skill kém/có hại: xóa và chạy lại curator (tối đa 2 lần), ghi lý do mỗi lần — không sửa tay nội dung skill
- [x] [run] `python -m lab.runner --condition skills-auto --tasks learn`
- [x] [report] Đối chiếu `skills_read` và `trace.md` xem skill có được dùng/làm theo không

## Phần 4. Giả thuyết, đóng băng, đo trên tác vụ đánh giá

- [x] [report] Viết giả thuyết H1-H3 vào mục 2 báo cáo (trước khi thấy điểm eval)
- [x] [run] `git add -A && git commit -m "hypotheses"`
- [x] [run] `git add -A && git commit --allow-empty -m "freeze skills" && git tag freeze`
- [x] [run] `python -m lab.runner --condition baseline --tasks eval`
- [x] [run] `python -m lab.runner --condition subagents --tasks eval`
- [x] [run] (trước khi ghi đè) sao lưu `mv results/skills-auto results/skills-auto-dev`
- [x] [run] `python -m lab.runner --condition skills-auto --tasks all`
- [x] [run] `python scripts/verify_freeze.py` → kỳ vọng `OK`
- [x] [fix bug] Nếu một lần chạy lỗi: chạy lại lần đó, ghi chú trong báo cáo
- [x] [run] `python -m lab.compare > report/table.md`
- [x] [run] `python scripts/check_breakdown.py` (dữ liệu cho mục 4, 7, 8 báo cáo)

## Phần 5. Báo cáo

- [x] [report] Hoàn thiện `report/REPORT.md` mục 1–7 (bản nháp trong buổi học)
- [x] [report] Dán bảng `report/table.md` vào mục 7
- [x] [report] Trả lời đủ 6 câu phân tích ở mục 8 (có số liệu)
- [x] [report] Hoàn thiện mục 9 (≥3 hạn chế) và mục 10 (kết luận, tối đa 5 câu)

## Phần 6. Thử thách mở rộng (tùy chọn, +5 điểm)

- [ ] [code] Chọn 1 hướng (6a-6e) và triển khai
- [ ] [run] Chạy thí nghiệm, ghi kết quả vào thư mục `results/` riêng
- [ ] [report] Viết phụ lục: hướng chọn, kết quả, nhận xét, hạn chế, đề xuất tiếp theo

## Nộp bài

- [x] [report] Kiểm tra đủ: `src/lab/*.py` (4 tệp), `skills/auto/`, `results/` (run.json + trace.md), `report/REPORT.md`, `report/table.md`
- [x] [fix bug] Không commit `.env`, không để lộ API key trong code/vết/báo cáo

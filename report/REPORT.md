# Báo cáo Lab: Self evolving Agentic

> Sao chép tệp này thành `report/REPORT.md` (đã làm ở Phần 0) và điền dần qua các Phần của lab. Xóa các dòng hướng dẫn dạng trích dẫn (bắt đầu bằng `>`). Văn phong kỹ thuật, ngắn gọn, mọi nhận định đi kèm số liệu hoặc bằng chứng. Trong buổi học: điền mục 1 đến 7 (bản nháp). Sau buổi học: hoàn thiện mục 8 đến 10.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| | | |

- Mô hình (tên deployment hoặc `LAB_MODEL`), nhiệt độ (`LAB_TEMPERATURE`), `recursion_limit`:
- Phiên bản Deep Agents (`pip show deepagents`), hệ điều hành, chạy trực tiếp hay trong Docker:
- Số lần chạy tác vụ đã dùng / ngân sách:
- Commit của tag `freeze`:

## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)

> Dự đoán điều kiện nào đạt điểm cao nhất trên **tác vụ đánh giá** và vì sao. Nêu căn cứ từ phân loại lỗi (mục 4) và từ tài liệu tham khảo. Điền cả ba dòng; `verify_freeze.py` kiểm tra điều này.

- H1 (subagents so với baseline): `subagents` sẽ KHÔNG đạt điểm cao hơn `baseline` trên tác vụ đánh giá (chênh lệch trong khoảng nhiễu, tối đa +-1 check mỗi tác vụ) và sẽ tốn nhiều token hơn rõ rệt (dự đoán từ 3 lần trở lên). Căn cứ: ở tác vụ học, mọi check thất bại của `baseline` đều là check quy ước (`rule_*`) hoặc `tests_not_modified`, tức là thông tin mà đề bài không nêu; giao việc cho subagent không tạo ra thông tin mới, chỉ chia nhỏ việc. Cả hai điều kiện đều đạt đúng 6/10, 5/8, 6/9 ở tác vụ học dù `subagents` tốn 3 đến 7 lần token.
- H2 (skills-auto so với baseline): `skills-auto` sẽ đạt điểm cao hơn `baseline` trên tác vụ đánh giá, chủ yếu ở các check quy ước dùng lại từ tác vụ học (ví dụ: tiền tính bằng cent, tệp `clean.csv`, chú thích kiểu, test hồi quy, changelog), nhưng KHÔNG giúp check quy ước mới chỉ có ở tác vụ đánh giá. Căn cứ: skill do curator viết từ chính các `detail` của check thất bại; nghiên cứu SkillsBench cho thấy skill tự sinh có lợi không ổn định, nên dự đoán lợi ích vừa phải, không đạt toàn bộ.
- H3 (tác vụ học so với tác vụ đánh giá): mức tăng điểm của `skills-auto` trên tác vụ học sẽ lớn hơn mức tăng trên tác vụ đánh giá (dấu hiệu quá khớp/khó chuyển giao), vì tác vụ đánh giá đổi dữ liệu và thêm một quy ước mới mà skill không biết.

## 3. Làm quen Deep Agents (Phần 0.3)

1. Công cụ mặc định (theo `scripts/tour.py`): `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep` (công cụ tệp), `execute` (shell) và `task` (giao việc cho subagent). Chỉ `execute` cho phép chạy lệnh.
2. Mô tả của `task` nói subagent `general-purpose` là tác tử đa dụng ("researching complex questions, searching for files and content, and executing multi-step tasks") và "has access to all tools as the main agent". Mỗi lần gọi là một subagent mới, không có trạng thái: nó chỉ nhìn thấy prompt do tác tử chính gửi ("the agent sees only the prompt you give it and returns a single final report"), không thấy lịch sử hội thoại của tác tử chính.
3. Câu hướng dẫn hành vi trích từ `task`: "Launch multiple agents concurrently when their tasks are independent, using a single message with multiple tool calls." Câu trích từ `execute`: "Quote paths containing spaces" và "Use absolute paths and avoid `cd` so the working directory stays stable". System prompt mặc định rỗng; lab dùng `BASE_PROMPT` để cố định quy ước đường dẫn tương đối.

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

> Chỉ dùng tác vụ học. Mỗi dòng là một check thất bại.

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng (trích ngắn từ `detail` hoặc vết) |
|---|---|---|---|
| code-learn | rule_type_hints | E | "RULE: every public function ... has type annotations on all parameters and on the return value." |
| code-learn | rule_regression_tests | E | "RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3)" |
| code-learn | rule_changelog | E | "RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' ..." |
| code-learn | tests_not_modified | G (kiểm tra ràng buộc: sửa tệp test gốc) | "the original files in tests/ must not be modified (new test files are allowed)" |
| data-learn | rule_money_in_cents | E | "RULE: money values in answer.json are integer cents (1606.67 USD is written 160667)." |
| data-learn | rule_meta_block | E | "RULE: answer.json has an object `meta` = {source, rows_in, rows_used}" |
| data-learn | rule_clean_csv | E | "RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents ..." |
| logs-learn | rule_service_names | E | "RULE: service names ... lower-case with '-' replaced by '_'" |
| logs-learn | rule_sorted_errors | E | "RULE: `errors` is sorted by service, then by timestamp_utc, ascending." |
| logs-learn | rule_schema_header | E | `"schema_version": 2 and "generated_by": "log-triage"` |

Số liệu `baseline`: code-learn 6/10, data-learn 5/8, logs-learn 6/9; tổng 17/27 check đạt, 10 check thất bại. 9 trong 10 check thất bại thuộc nhóm E (tên check bắt đầu bằng `rule_`), 1 thuộc nhóm G (`tests_not_modified`). Tất cả check kỹ thuật (nhóm A đến D: giá trị đúng, đọc đặc tả, dữ liệu bẩn, múi giờ) đều đạt ở cả ba tác vụ, đó là bằng chứng phủ định cho các nhóm A đến D (xem `scripts/check_breakdown.py` ở mục 7). Nhận xét: nhóm E chiếm đa số vì quy ước của tổ chức không nằm trong đề bài; một skill ghi lại các quy ước đó dưới dạng danh sách kiểm tra có thể phòng ngừa nhóm này, với điều kiện tác tử đọc skill và quy ước đó cũng xuất hiện ở tác vụ mới.

## 5. Điều kiện `subagents` (Phần 2.3)

- Các subagent đã định nghĩa (tên, vai trò, lý do thiết kế): `explorer` (chỉ đọc, báo cáo quy tắc và nguyên nhân gốc), `implementer` (sửa mã hoặc ghi tệp rồi chạy kiểm chứng), `reviewer` (kiểm tra độc lập, không sửa). Ba vai trò tương ứng với quy trình đọc, làm, kiểm tra; `description` viết dưới dạng chỉ dẫn "dùng khi nào" và nhắc phải đưa toàn bộ quy tắc vào lời giao việc vì subagent chỉ thấy prompt.
- `subagent_calls` ở từng tác vụ và nhận xét (kể cả trường hợp bằng 0): code-learn 9, data-learn 3, logs-learn 4. Tác tử chính luôn giao việc ít nhất một lần, nên không có trường hợp bằng 0. Số `tool_calls` ở luồng chính thấp (13, 4, 7) vì phần lớn việc diễn ra bên trong subagent và không hiện trong `trace.md`.
- Thông tin thiếu hoặc thừa khi giao việc (nếu có giao việc): các lời giao việc chuyển lại đề bài nhưng không có quy ước của tổ chức, vì đề bài cũng không nêu quy ước đó; các check `rule_*` vẫn thất bại giống hệt `baseline`. Subagent không tạo thêm thông tin mới.
- Ảnh hưởng đến token và thời gian: token tổng của `subagents` lần lượt là 469.100, 444.487, 425.031 so với 138.348, 159.551, 60.831 của `baseline` (gấp 3,4 / 2,8 / 7,0 lần) với cùng điểm (6/10, 5/8, 6/9). Thời gian code-learn 452 giây so với 93 giây. Con số 5112 giây của logs-learn ở `subagents` không phản ánh thời gian chạy thật: máy bị tạm dừng/mất kết nối giữa lần chạy và lần chạy đó được thực hiện lại sau lỗi mạng `getaddrinfo failed`.

## 6. Self-evolving: skill do curator sinh (Phần 3)

- Số lần chạy curator, số skill bị xóa và lý do: 3 lần chạy (1 lần đầu + 2 lần chạy lại, đúng mức tối đa của GUIDE 3.3).
  - Lần 1: 2 skill (`adhere-to-strict-rules-and-conventions`, `comprehensive-code-quality-and-testing`). Cả hai bị xóa vì quá chung chung ("check every explicit rule", "add type annotations"): ở Phần 3.4, `skills_read` = 2 ở cả ba tác vụ học nhưng điểm không đổi so với `baseline` (6/10, 5/8, 6/9, cùng đúng 10 check thất bại), tức skill được đọc mà không giúp được gì vì không nêu nội dung quy ước. Bản sao ở `results/_curator_run1/`, kết quả chạy ở `results/skills-auto-dev-v1/`.
  - Lần 2: sau khi sửa `PROMPT` của curator (yêu cầu nêu nguyên văn từng quy tắc `rule_*` dưới dạng danh sách kiểm tra có định dạng cụ thể), ra `python-code-modifications`, `log-file-analysis`; skill dữ liệu bảng bị `validate_skill` từ chối vì chứa chữ `orders` ("mentions evaluation material: orders"). Bản sao ở `results/_curator_run2/`.
  - Lần 3: ra `python-code-fixing-conventions`, `log-analysis-conventions` (nội dung trùng hai skill của lần 2) và skill dữ liệu bảng lại bị từ chối vì cùng lý do. Hai skill của lần 2 bị xóa vì trùng lặp; giữ hai skill của lần 3. Không sửa tay nội dung skill nào. Hệ quả: bộ skill đóng băng KHÔNG có skill cho họ `data`, nên `skills-auto` không thể giúp tác vụ dữ liệu; đây là cái giá của biện pháp chống rò rỉ (chữ `orders` là định danh của tác vụ đánh giá, nhưng curator dùng nó như một từ thông thường).

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai (nêu chỗ sai nếu có) | Độ dài, `description` và `skills_read` ở Phần 3.4 |
|---|---|---|---|
| `python-code-fixing-conventions` | Tổng quát theo họ tác vụ "sửa gói Python"; không nêu tên hàm, tệp hay số riêng của `code-learn`. Chỉ có các tên do quy ước yêu cầu (`tests/test_regressions.py`, `CHANGELOG.md`, `## Unreleased`). | Đúng: khớp nguyên văn các `detail` của bot đánh giá ở `code-learn`. Không có hướng dẫn sai hoặc gây hại. | 5 dòng; `description` bắt đầu bằng "Use when" nêu loại tác vụ rộng. `skills_read` = 1 (code-learn). |
| `log-analysis-conventions` | Tổng quát theo họ "phân tích log thành JSON"; chỉ nêu các quy ước (tên dịch vụ, thứ tự sắp xếp, `schema_version`). | Đúng: khớp các `detail` của `logs-learn`. Có hạn chế: là bản sao gần như nguyên văn của `detail`, nên có nguy cơ quá khớp với đúng bộ quy ước đã thấy. | 4 dòng; `description` nêu "parsing application log files". `skills_read` = 1 (logs-learn). |

Kết quả Phần 3.4 với bộ skill cuối: code-learn 9/10 (từ 6/10), logs-learn 9/9 (từ 6/9), data-learn 5/8 (không đổi, không có skill). Trong `trace.md`, tác tử đọc skill ngay đầu lượt rồi áp dụng; check còn thất bại ở code-learn là `tests_not_modified`, mặc dù skill nêu "do not modify any existing files in `tests/`". Lần chạy code-learn này kết thúc bằng `GraphRecursionError` ở bước 60 nhưng vẫn được chấm trên workspace hiện có (9/10).

## 7. Kết quả so sánh (Phần 4.3, 4.4)

> Dán nội dung `report/table.md` và kết quả `python scripts/check_breakdown.py`. Nêu các lần chạy có `error` hoặc `skills_modified = true` (nếu có) và cách xử lý.

```text
(dán bảng ở đây)
```

## 8. Phân tích

> Trả lời từng câu bằng số liệu từ mục 7 và bằng chứng từ vết. Kết quả âm hoặc không có khác biệt vẫn hợp lệ nếu được phân tích tốt.

1. So với `baseline`, điều kiện nào cải thiện điểm tác vụ **học**? Điều kiện nào cải thiện điểm tác vụ **đánh giá**? Có điều kiện nào cải thiện tác vụ học nhưng không cải thiện tác vụ đánh giá? Nếu có, đó là dấu hiệu gì?
2. Tách điểm thành check kỹ thuật và check quy ước (`rule_`). Skill do curator sinh giúp nhóm check nào? Check quy ước **mới** của tác vụ đánh giá có được skill giúp không, và vì sao?
3. Dựa vào vết và `skills_read`, giải thích một check mà skill giúp đạt và một check mà skill không giúp (skill chưa được đọc, đọc nhưng không làm theo, skill thiếu hoặc sai).
4. Chi phí: so sánh số token trung bình giữa các điều kiện. Điều kiện nào có hiệu quả tốt nhất theo điểm trên mỗi token? Đa tác tử có đáng chi phí trong thí nghiệm này không?
5. Có dấu hiệu rò rỉ dữ liệu hoặc quá khớp nào trong skill sinh ra không? Nhóm đã phòng tránh như thế nào?
6. Nhiễu: so sánh điểm tác vụ học của cùng bộ skill ở Phần 3.4 (đã sao lưu) và sau đóng băng. Chênh lệch bao nhiêu? Nó cho biết điều gì về độ tin cậy của các chênh lệch trong bảng ở mục 7?

## 9. Hạn chế và tính hợp lệ

> Nêu ít nhất 3 hạn chế và ảnh hưởng của từng hạn chế đến kết luận (ví dụ: chỉ 3 tác vụ mỗi vai trò, mỗi cấu hình chạy một lần, nhiễu của mô hình, tác vụ do giảng viên thiết kế sẵn quy ước, chỉ một mô hình).

1.
2.
3.

## 10. Kết luận

> Tối đa 5 câu. Chỉ khẳng định điều số liệu hỗ trợ. Nêu một đề xuất cải tiến tiếp theo.

## Phụ lục

- Lệnh đã chạy (theo thứ tự):
- Thử thách mở rộng (nếu có): hướng chọn, kết quả, nhận xét.
- Ghi chú khác:

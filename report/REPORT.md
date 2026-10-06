# Báo cáo Lab: Self evolving Agentic

> Sao chép tệp này thành `report/REPORT.md` (đã làm ở Phần 0) và điền dần qua các Phần của lab. Xóa các dòng hướng dẫn dạng trích dẫn (bắt đầu bằng `>`). Văn phong kỹ thuật, ngắn gọn, mọi nhận định đi kèm số liệu hoặc bằng chứng. Trong buổi học: điền mục 1 đến 7 (bản nháp). Sau buổi học: hoàn thiện mục 8 đến 10.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Vũ Việt Hoàng | 2A202602398 | Toàn bộ lab (thực hiện cá nhân) |

- Mô hình, nhiệt độ, `recursion_limit`: `LAB_MODEL=google_genai:gemini-3.5-flash-lite`, tự chuyển sang `gemini-3.1-flash-lite` khi hết hạn mức ngày (`src/lab/gemini.py`); `LAB_TEMPERATURE=0`; `recursion_limit=60` (mặc định của runner).
- Phiên bản Deep Agents, hệ điều hành, chạy trực tiếp hay trong Docker: `deepagents==0.7.21`, Windows 11, chạy trực tiếp (shell của tác tử là Git Bash).
- Số lần chạy tác vụ đã dùng / ngân sách: 18 lần chạy chính thức (6 tác vụ x 3 điều kiện), cộng 6 lần chạy `skills-auto` ở Phần 3.4 (hai bộ skill) và 3 lần curator. Ngân sách Gemini được ép trong code: tối đa 14 request mỗi phút, khoảng 225K token mỗi phút, 499 request mỗi ngày cho mỗi mô hình. Trong ngày chạy chính thức dùng 463 request cho `gemini-3.5-flash-lite` (hết hạn mức ngày, đổi mô hình giữa lần chạy `skills-auto` của `data-learn`) và 36 cho `gemini-3.1-flash-lite`.
- Commit của tag `freeze`: `e6103b9` (commit `hypotheses` là `f5a6911`).

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
| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 6/10 | 6/10 | 9/10 |
| data-learn | 5/8 | 5/8 | 4/8 |
| logs-learn | 6/9 | 6/9 | 9/9 |
| code-eval | 6/11 | 6/11 | 9/11 |
| data-eval | 5/9 | 4/9 | 5/9 |
| logs-eval | 6/10 | 6/10 | 9/10 |
| **Mean score - learning tasks** | 0.63 | 0.63 | 0.80 |
| **Mean score - evaluation tasks** | 0.57 | 0.53 | 0.76 |
| **Mean tokens per run** | 111,304 | 426,945 | 112,770 |
| **Runs that read a skill** | 0/6 | 0/6 | 6/6 |

condition     role    technical  house rules  mean tokens  read a skill
baseline      eval     17/18         0/12         103,032      0/3     
baseline      learn    17/18         0/9          119,576      0/3     
subagents     eval     16/18         0/12         407,684      0/3     
subagents     learn    17/18         0/9          446,206      0/3     
skills-auto   eval     17/18         6/12          94,872      3/3     
skills-auto   learn    16/18         6/9          130,668      3/3
```

Ghi chú về các lần chạy:

- `verify_freeze.py` (chạy với `PYTHONUTF8=1` vì script đọc báo cáo tiếng Việt; không sửa script): `checked 6 runs of skill conditions: OK`.
- Không có lần chạy chính thức nào có `error` hoặc `skills_modified = true`. Riêng ở Phần 3.4 (bộ skill cuối), `code-learn` kết thúc bằng `GraphRecursionError` (bước 60) nhưng vẫn được chấm trên workspace hiện có.
- Check `tests_not_modified` thất bại ở MỌI điều kiện của hai tác vụ `code-*` (kể cả `baseline`). Nguyên nhân: Git trên Windows có `core.autocrlf=true` nên `tasks/*/workspace/tests/test_bookings.py` được checkout dạng CRLF, còn `check.py` so băm SHA-256 với bản LF (băm trên đĩa `9e82bb53...` so với bản chuẩn hóa LF `9d29eae4...`). Đây là sai lệch môi trường, không phải lỗi của tác tử, và nó trừ đúng 1 check ở mọi ô của code-learn và code-eval, nên không làm lệch so sánh giữa các điều kiện.
- Lần chạy `skills-auto` của `data-learn` sau freeze đổi mô hình giữa chừng từ `gemini-3.5-flash-lite` sang `gemini-3.1-flash-lite` (hết hạn mức ngày): đây là một nguồn nhiễu.
- Lần chạy `subagents` của `logs-learn` bị lỗi mạng `getaddrinfo failed` ở lần đầu và được chạy lại; thời gian 5112 giây của kết quả cuối không phản ánh thời gian chạy thật (phiên làm việc bị gián đoạn trong lúc chạy).

## 8. Phân tích

> Trả lời từng câu bằng số liệu từ mục 7 và bằng chứng từ vết. Kết quả âm hoặc không có khác biệt vẫn hợp lệ nếu được phân tích tốt.

1. So với `baseline`, điều kiện nào cải thiện điểm tác vụ **học**? Điều kiện nào cải thiện điểm tác vụ **đánh giá**? Có điều kiện nào cải thiện tác vụ học nhưng không cải thiện tác vụ đánh giá? Nếu có, đó là dấu hiệu gì?

   Điểm trung bình tác vụ học: `baseline` 0,63, `subagents` 0,63, `skills-auto` 0,80 (+0,17). Tác vụ đánh giá: `baseline` 0,57, `subagents` 0,53 (-0,04), `skills-auto` 0,76 (+0,19). Chỉ `skills-auto` cải thiện, ở cả hai vai trò, với mức tăng tương đương (0,17 so với 0,19), nên trong thí nghiệm này KHÔNG có dấu hiệu quá khớp theo nghĩa "tăng ở học nhưng không tăng ở đánh giá". Điều này không bác bỏ nguy cơ quá khớp nói chung: tác vụ đánh giá được thiết kế để dùng lại các quy ước của tác vụ học, nên việc chuyển giao dễ hơn so với một tác vụ thật sự mới. `subagents` không cải thiện điểm nào (data-eval còn kém 1 check). Giả thuyết H3 (mức tăng ở học lớn hơn ở đánh giá) không được ủng hộ; H1 và H2 được ủng hộ.
2. Tách điểm thành check kỹ thuật và check quy ước (`rule_`). Skill do curator sinh giúp nhóm check nào? Check quy ước **mới** của tác vụ đánh giá có được skill giúp không, và vì sao?

   Check kỹ thuật gần như không đổi: tác vụ đánh giá 17/18 (`baseline`), 16/18 (`subagents`), 17/18 (`skills-auto`); tác vụ học 17/18, 17/18, 16/18. Check quy ước (house rules) ở tác vụ đánh giá: 0/12, 0/12, 6/12. Toàn bộ mức tăng của `skills-auto` đến từ check quy ước: 6 check dùng lại từ tác vụ học (`rule_type_hints`, `rule_regression_tests`, `rule_changelog` ở code-eval; `rule_service_names`, `rule_sorted_errors`, `rule_schema_header` ở logs-eval) đều đạt. Cả 3 check quy ước MỚI của tác vụ đánh giá (`rule_version_bump`, `rule_sorted_keys_format`, `rule_source_line`) đều không đạt ở mọi điều kiện, vì skill chỉ ghi các quy tắc đã thấy ở tác vụ học và tác tử không có cách nào đoán quy tắc mới. Họ `data` không được lợi gì (0/4 quy ước) vì bộ skill đóng băng không có skill dữ liệu (mục 6).
3. Dựa vào vết và `skills_read`, giải thích một check mà skill giúp đạt và một check mà skill không giúp (skill chưa được đọc, đọc nhưng không làm theo, skill thiếu hoặc sai).

   Giúp: `logs-eval`, `rule_service_names` đạt ở `skills-auto` và thất bại ở `baseline`. Trong `results/skills-auto/logs-eval/trace.md`, tác tử đọc `skills/log-analysis-conventions/SKILL.md` ngay lượt đầu (`skills_read` = 1) rồi xuất tên dịch vụ dạng chữ thường với `_`; điểm tăng từ 6/10 lên 9/10. Không giúp (skill thiếu): `data-eval`, cả 4 check quy ước thất bại vì không có skill dữ liệu; tác tử đọc cả hai skill (`skills_read` = 2) do `SKILLS_NOTE` bảo đọc mọi skill có thể áp dụng, nhưng nội dung không liên quan. Không giúp (quy tắc mới): `logs-eval`, `rule_source_line` vẫn thất bại dù đã đọc skill, vì skill không nêu quy tắc này. Không giúp (không do skill): `tests_not_modified`, thất bại ở mọi điều kiện do lỗi CRLF của môi trường (mục 7).
4. Chi phí: so sánh số token trung bình giữa các điều kiện. Điều kiện nào có hiệu quả tốt nhất theo điểm trên mỗi token? Đa tác tử có đáng chi phí trong thí nghiệm này không?

   Token trung bình mỗi lần chạy: `baseline` 111.304, `subagents` 426.945 (gấp 3,8 lần), `skills-auto` 112.770 (xấp xỉ `baseline`). Điểm trung bình toàn bộ 6 tác vụ: 0,60 / 0,58 / 0,78. Điểm trên mỗi 100K token: 0,54 / 0,14 / 0,69. `skills-auto` hiệu quả nhất; `subagents` không đáng chi phí ở đây: tốn gần gấp 4 lần token và thời gian (code-eval 476 giây so với 83 giây) mà không có điểm cao hơn, vì lỗi nằm ở quy ước ẩn chứ không ở năng lực chia việc.
5. Có dấu hiệu rò rỉ dữ liệu hoặc quá khớp nào trong skill sinh ra không? Nhóm đã phòng tránh như thế nào?

   Không phát hiện đáp án hay định danh của tác vụ đánh giá trong skill: `validate_skill` đã chặn hai lần skill dữ liệu vì chứa chữ `orders` (định danh của tác vụ đánh giá), curator chỉ đọc lần chạy có `role == "learn"`, và không sửa tay skill. Rủi ro còn lại là quá khớp kiểu khác: hai skill gần như sao chép nguyên văn các `detail` của bot đánh giá ở tác vụ học, nên chúng chỉ giúp khi tác vụ mới dùng lại đúng các quy ước đó, như đã thấy ở 6/6 quy ước dùng lại và 0/3 quy ước mới. Tag `freeze` được xác minh bằng `verify_freeze.py` (OK).
6. Nhiễu: so sánh điểm tác vụ học của cùng bộ skill ở Phần 3.4 (đã sao lưu) và sau đóng băng. Chênh lệch bao nhiêu? Nó cho biết điều gì về độ tin cậy của các chênh lệch trong bảng ở mục 7?

   Cùng bộ skill: code-learn 9/10 và 9/10, logs-learn 9/9 và 9/9, data-learn 5/8 so với 4/8. Chênh lệch tối đa là 1 check, ở lần chạy có đổi mô hình giữa chừng và có một check kỹ thuật (`north_q1_revenue`) thất bại. Do đó các chênh lệch cỡ 1 check (ví dụ `subagents` 4/9 so với `baseline` 5/9 ở data-eval) nằm trong khoảng nhiễu và không nên diễn giải; chênh lệch +3 check của `skills-auto` ở code và logs (cả học lẫn đánh giá, lặp lại ở hai lần chạy độc lập) lớn hơn nhiễu quan sát được.

## 9. Hạn chế và tính hợp lệ

> Nêu ít nhất 3 hạn chế và ảnh hưởng của từng hạn chế đến kết luận (ví dụ: chỉ 3 tác vụ mỗi vai trò, mỗi cấu hình chạy một lần, nhiễu của mô hình, tác vụ do giảng viên thiết kế sẵn quy ước, chỉ một mô hình).

1. Quy mô nhỏ và một lần chạy: chỉ 3 tác vụ mỗi vai trò, mỗi ô chạy một lần; nhiễu quan sát được là 1 check (data-learn 5/8 so với 4/8 cùng bộ skill), nên mọi chênh lệch cỡ 1 check (kể cả `subagents` kém `baseline` 1 check ở data-eval) không có ý nghĩa.
2. Quy ước do người thiết kế đặt sẵn và tác vụ đánh giá dùng lại chúng: lợi ích của `skills-auto` (+0,19) là cận trên cho việc chuyển giao; không suy ra được skill tự sinh giúp tác vụ có quy ước hoàn toàn mới (0/3 quy ước mới đạt).
3. Một mô hình nhỏ miễn phí (`gemini-3.5-flash-lite`), có đổi sang `gemini-3.1-flash-lite` giữa một lần chạy do hết hạn mức ngày; giới hạn tốc độ làm đổi thời gian chạy. Kết luận về `subagents` có thể khác với mô hình mạnh hơn.
4. Lỗi môi trường làm hỏng một check: `tests_not_modified` thất bại ở mọi điều kiện do CRLF (mục 7), nên điểm tối đa thực tế của hai tác vụ `code-*` là 9/10 và 10/11 ở mọi cột.
5. Bộ skill thiếu họ `data` vì bộ lọc chống rò rỉ chặn từ `orders`; kết quả `skills-auto` ở họ `data` vì vậy chỉ cho biết tác động của việc không có skill. Ngoài ra `PROMPT` của curator được chỉnh sau lần chạy đầu dựa trên kết quả ở tác vụ học (đã ghi ở mục 6): hợp lệ, nhưng bộ skill cuối được tối ưu theo tác vụ học.

## 10. Kết luận

> Tối đa 5 câu. Chỉ khẳng định điều số liệu hỗ trợ. Nêu một đề xuất cải tiến tiếp theo.

Skill do curator sinh ra tăng điểm trung bình tác vụ đánh giá từ 0,57 lên 0,76 với cùng mức token, nhưng chỉ nhờ các quy ước dùng lại từ tác vụ học (6/6 đạt) và không giúp quy ước mới (0/3). Đa tác tử tốn gấp khoảng 3,8 lần token mà không cải thiện điểm (0,53 so với 0,57 ở tác vụ đánh giá). Một skill chung chung mà tác tử đọc vẫn không giúp gì (lần curator đầu tiên); skill phải nêu nguyên văn quy tắc. Chỉ có 3 tác vụ mỗi vai trò và một lần chạy, nên cần lặp lại (hướng 6e) trước khi kết luận chắc chắn. Đề xuất: sửa bộ lọc rò rỉ để không chặn nhầm từ thông thường như `orders`, và thêm bước cho tác tử tự kiểm tra lại các quy ước trước khi kết thúc.

## Phụ lục

- Lệnh đã chạy (theo thứ tự): `pytest tests` (37 test, ngoại tuyến); `python scripts/tour.py`; `python -m lab.runner --condition baseline --tasks learn`; `... --condition subagents --tasks learn`; `python -m lab.curator` (3 lần); `... --condition skills-auto --tasks learn`; `git commit -m hypotheses`; `git commit --allow-empty -m "freeze skills" && git tag freeze`; `... --condition baseline --tasks eval`; `... --condition subagents --tasks eval`; `mv results/skills-auto results/skills-auto-dev`; `... --condition skills-auto --tasks all`; `PYTHONUTF8=1 python scripts/verify_freeze.py`; `python -m lab.compare > report/table.md`; `python scripts/check_breakdown.py`.
- Thử thách mở rộng (nếu có): không thực hiện.
- Ghi chú khác: `results/skills-auto-dev-v1/` là kết quả Phần 3.4 của bộ skill lần curator đầu (đã xóa); `results/skills-auto-dev/` là kết quả Phần 3.4 của bộ skill cuối, sao lưu trước khi chạy lại sau freeze; `results/_curator_run1/` và `results/_curator_run2/` lưu các skill bị xóa. Ba thư mục này (tên không thuộc ba điều kiện) không được `lab.compare` đọc. Ngân sách API được giới hạn trong `src/lab/gemini.py` (RPM, token mỗi phút, request mỗi ngày, tự đổi mô hình).

# WallE3 VLM — BA/PM Implementation Plan

## 1. Mục tiêu

Biến project **WallE3 VLM** từ một demo kỹ thuật robotics thành một **portfolio case study cho vị trí Business Analyst / Product Manager** trong công ty robotics.

Trọng tâm không chỉ là robot chạy được, mà là chứng minh năng lực BA/PM qua:

- Hiểu bài toán người dùng và business context.
- Chuyển tính năng kỹ thuật thành requirement rõ ràng.
- Xây backlog, acceptance criteria và test plan.
- Định nghĩa KPI, telemetry và dashboard spec.
- Quản trị rủi ro an toàn cho robot.
- Lập roadmap từ MVP kỹ thuật đến pilot readiness.

---

## 2. Định vị project

**Tên case study:**

> WallE3 VLM — Natural-language autonomous service robot for warehouse / mall operation

**Thông điệp chính:**

> Productized a ROS 2 + VLM autonomous robot prototype into a BA/PM-ready robotics MVP by defining product requirements, user journeys, KPI framework, safety risks, UAT scenarios, delivery governance, and release roadmap.

---

## 3. Phạm vi triển khai

### In scope

- Product one-pager.
- Business Requirements Document.
- Product Requirements Document.
- Personas và user journey.
- Service blueprint.
- Product backlog và user stories.
- Requirements traceability matrix.
- KPI dashboard specification.
- Event contract documentation.
- Risk register / FMEA-lite.
- UAT test plan.
- Release roadmap.
- Pilot rollout plan.
- GitHub issue templates.
- Pull request template.
- Portfolio interview pitch.

### Out of scope ở giai đoạn này

- Build dashboard thật.
- Deploy robot thật ngoài simulation.
- Multi-robot fleet management.
- Production-grade SLAM/navigation.
- Full hardware certification.

---

## 4. Deliverables cần tạo

```text
docs/product/
  README.md
  00_portfolio_case_study.md
  01_product_one_pager.md
  02_business_requirements_document.md
  03_product_requirements_document.md
  04_personas_user_journey.md
  05_service_blueprint.md
  06_backlog_user_stories.md
  07_requirements_traceability_matrix.md
  08_kpi_dashboard_spec.md
  09_event_contract_v1.md
  10_risk_register_fmea.md
  11_uat_test_plan.md
  12_release_roadmap.md
  13_stakeholder_communication_plan.md
  14_pilot_rollout_plan.md
  15_postmortem_template.md
  16_interview_pitch.md
  17_roi_tco_one_pager.md
  18_product_decision_log.md
  19_readme_insert.md

.github/
  ISSUE_TEMPLATE/
    feature_request.md
    bug_report.md
    safety_issue.md
    experiment_report.md
    uat_failure.md
  PULL_REQUEST_TEMPLATE.md

ISSUES.md
README_BA_PM_PACKAGE.md
```

---

## 5. Thứ tự ưu tiên triển khai

## P0 — Bắt buộc có để ứng tuyển

| Hạng mục | Mục đích | Output |
|---|---|---|
| Portfolio case study | Kể câu chuyện project theo góc nhìn BA/PM | `00_portfolio_case_study.md` |
| Product one-pager | Tóm tắt problem, users, solution, value | `01_product_one_pager.md` |
| BRD | Mô tả business problem và business requirements | `02_business_requirements_document.md` |
| PRD | Chuyển ý tưởng thành functional / non-functional requirements | `03_product_requirements_document.md` |
| Backlog user stories | Thể hiện năng lực viết user story và acceptance criteria | `06_backlog_user_stories.md` |
| KPI dashboard spec | Chứng minh tư duy data-driven PM | `08_kpi_dashboard_spec.md` |
| Risk register | Chứng minh hiểu safety trong robotics | `10_risk_register_fmea.md` |
| UAT test plan | Chứng minh năng lực validation và testing | `11_uat_test_plan.md` |
| Release roadmap | Cho thấy tư duy product strategy | `12_release_roadmap.md` |

## P1 — Nên có để nổi bật

| Hạng mục | Mục đích | Output |
|---|---|---|
| Personas & journey | Chứng minh hiểu người dùng | `04_personas_user_journey.md` |
| Service blueprint | Map user action, robot action, telemetry, support | `05_service_blueprint.md` |
| Traceability matrix | Kết nối business goal → requirement → test case | `07_requirements_traceability_matrix.md` |
| Event contract | Chuẩn hóa event phục vụ analytics | `09_event_contract_v1.md` |
| Stakeholder communication plan | Thể hiện năng lực quản trị stakeholder | `13_stakeholder_communication_plan.md` |
| Pilot rollout plan | Chuẩn bị cho triển khai thực tế | `14_pilot_rollout_plan.md` |
| Product decision log | Ghi lại quyết định sản phẩm | `18_product_decision_log.md` |

## P2 — Bổ sung để giống môi trường công ty thật

| Hạng mục | Mục đích | Output |
|---|---|---|
| GitHub issue templates | Chuẩn hóa intake bug/feature/safety issue | `.github/ISSUE_TEMPLATE/` |
| Pull request template | Chuẩn hóa delivery governance | `.github/PULL_REQUEST_TEMPLATE.md` |
| ROI/TCO one-pager | Thể hiện góc nhìn business case | `17_roi_tco_one_pager.md` |
| Postmortem template | Chuẩn bị xử lý incident / failed experiment | `15_postmortem_template.md` |
| README insert | Thêm phần BA/PM vào README chính | `19_readme_insert.md` |

---

## 6. Kế hoạch triển khai 7 ngày

| Ngày | Việc cần làm | Kết quả mong muốn |
|---|---|---|
| Day 1 | Viết portfolio case study và product one-pager | Có câu chuyện project rõ ràng để đưa vào CV/GitHub |
| Day 2 | Viết personas, user journey và service blueprint | Làm rõ ai dùng robot, dùng khi nào, pain point là gì |
| Day 3 | Viết BRD và PRD | Có bộ requirements chuẩn BA/PM |
| Day 4 | Viết backlog, user stories và acceptance criteria | Có backlog đủ để phỏng vấn hoặc demo quy trình product |
| Day 5 | Viết KPI dashboard spec và event contract | Liên kết telemetry kỹ thuật với product metrics |
| Day 6 | Viết risk register và UAT test plan | Chứng minh năng lực safety, validation, QA mindset |
| Day 7 | Viết roadmap, issue templates, README insert và polish repo | Repo sẵn sàng dùng làm portfolio ứng tuyển |

---

## 7. KPI cần nhấn mạnh trong project

| KPI | Ý nghĩa |
|---|---|
| Mission success rate | Robot hoàn thành nhiệm vụ với tỷ lệ bao nhiêu |
| Mean mission duration | Trung bình mỗi nhiệm vụ mất bao lâu |
| Operator intervention count | Người vận hành phải can thiệp bao nhiêu lần |
| Safety event rate | Số sự kiện an toàn trên mỗi mission |
| Stop command latency | Robot dừng nhanh đến mức nào sau lệnh stop |
| VLM inference latency p50/p95 | Độ trễ suy luận của model |
| Stuck abort rate | Tỷ lệ nhiệm vụ bị hủy vì robot kẹt |
| Target not found rate | Tỷ lệ robot không tìm thấy mục tiêu |

---

## 8. Roadmap sản phẩm đề xuất

| Release | Mục tiêu | Nội dung chính |
|---|---|---|
| R0 — Technical MVP | Robot demo chạy được trong simulation | VLM planner, safety loop, cmd_vel mux, mission logger |
| R1 — Productized MVP | Repo sẵn sàng cho BA/PM portfolio | PRD, BRD, backlog, KPI, UAT, risk, roadmap |
| R2 — Operator Experience | Cải thiện trải nghiệm người vận hành | Vietnamese command, voice input, status panel, command confirmation |
| R3 — Pilot Readiness | Chuẩn bị triển khai thử nghiệm thực tế | Spatial memory, privacy policy, hardware checklist, pilot rollout plan |
| R4 — Production Readiness | Hướng tới sản phẩm vận hành ổn định | Monitoring, incident process, fleet support, support playbook |

---

## 9. Checklist hoàn thành

### Product documentation

- [ ] Có product one-pager.
- [ ] Có BRD.
- [ ] Có PRD.
- [ ] Có personas và user journey.
- [ ] Có service blueprint.
- [ ] Có backlog user stories.
- [ ] Có acceptance criteria rõ ràng.
- [ ] Có requirements traceability matrix.

### Robotics product readiness

- [ ] Có KPI dashboard spec.
- [ ] Có event contract.
- [ ] Có risk register / FMEA-lite.
- [ ] Có UAT test plan.
- [ ] Có pilot rollout plan.
- [ ] Có postmortem template.

### GitHub governance

- [ ] Có issue templates.
- [ ] Có pull request template.
- [ ] Có `ISSUES.md`.
- [ ] Có README insert cho phần BA/PM.
- [ ] Có roadmap rõ ràng.

### Portfolio readiness

- [ ] Có case study ngắn gọn.
- [ ] Có interview pitch 30s / 60s / 2 phút.
- [ ] Có bullet CV.
- [ ] Có ảnh, video hoặc GIF demo nếu có thể.
- [ ] Có link GitHub được tổ chức dễ đọc.

---

## 10. Cách dùng trong CV

Gợi ý bullet:

> Productized a ROS 2 + VLM autonomous robot MVP into a BA/PM-ready robotics product case by defining BRD, PRD, user journey, backlog, traceability matrix, KPI dashboard spec, event contract, UAT plan, safety risk register, issue governance, and release roadmap from technical MVP to pilot readiness.

Gợi ý bullet ngắn hơn:

> Built BA/PM documentation for an autonomous robotics MVP, covering product requirements, safety risks, telemetry KPIs, UAT scenarios, backlog, and roadmap.

---

## 11. Cách trình bày khi phỏng vấn

### Pitch 30 giây

WallE3 là robot ROS 2 dùng Vision-Language Model để nhận lệnh tự nhiên như “go to the orange box”. Tôi productize project này thành một case study BA/PM bằng cách viết BRD, PRD, backlog, KPI framework, UAT test plan, risk register và roadmap. Điểm tôi muốn thể hiện là khả năng biến một prototype kỹ thuật robotics thành một MVP có yêu cầu, metric, safety governance và kế hoạch pilot rõ ràng.

### Điểm cần nhấn mạnh

- Robotics product không chỉ cần AI chạy được, mà cần safety, observability và validation.
- BA/PM cần nối business goal với requirement, telemetry và test case.
- Project này thể hiện khả năng làm việc với cả engineering, QA, operations và stakeholder business.

---

## 12. Lệnh triển khai vào repo

```bash
git checkout -b product/ba-pm-docs

mkdir -p docs/product
mkdir -p .github/ISSUE_TEMPLATE

# Copy toàn bộ file documentation và template vào repo
# Sau đó commit:

git add docs/product .github ISSUES.md README_BA_PM_PACKAGE.md
git commit -m "Productize WallE3 with BA PM documentation"
```

---

## 13. Kết quả kỳ vọng

Sau khi hoàn thành, repo không chỉ là một robotics demo mà trở thành một **BA/PM portfolio project hoàn chỉnh**, thể hiện được:

- Product thinking.
- Business analysis.
- Requirements management.
- Delivery planning.
- Robotics safety mindset.
- Data-driven product management.
- Stakeholder communication.
- Pilot and release planning.


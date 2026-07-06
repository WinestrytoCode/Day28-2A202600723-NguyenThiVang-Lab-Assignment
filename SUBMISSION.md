# Hướng Dẫn Nộp Bài - Lab #28: Full Platform Integration Sprint

## Yêu Cầu Nộp Bài

**Full AI infrastructure platform demo** - từ data ingestion đến model serving với full observability.

## Các Artifacts Cần Nộp

### 1. Source Code
- Folder `lab28/` hoàn chỉnh với tất cả files
- Tất cả integration scripts hoạt động
- Prefect flows đã deploy và schedule

### 2. Screenshots Demo
Chụp màn hình các bước:
- Prefect UI: http://localhost:4200 (flow đang chạy)
- API Gateway call: `curl http://localhost:8000/health`
- Grafana dashboard: http://localhost:3000

### 3. Kết Quả Smoke Tests
Chạy và chụp màn hình kết quả:
```bash
cd lab28
pytest smoke-tests/ -v
```
Kỳ vọng: 5/5 tests passing

### 4. Production Readiness Score
```bash
python scripts/production_readiness_check.py
```
Kỳ vọng: Score >80%

### 5. Documentation
- `README.md` giải thích cách:
  - Start platform: `docker compose up -d`
  - Deploy Prefect flows
  - Run smoke tests
  - Access dashboards (Grafana:3000, Prometheus:9090, Prefect:4200)

## Định Dạng Nộp Bài

Tạo Repo GitHub chứa:
```
lab28_submission_[student_id]
├── lab28/                    # Source code hoàn chỉnh
│   ├── docker-compose.yml
│   ├── prefect/flows/
│   ├── scripts/
│   ├── api-gateway/
│   └── monitoring/
├── screenshots/              # Screenshots demo
│   ├── prefect_ui.png
│   ├── api_gateway.png
│   └── grafana_dashboard.png
├── smoke_tests_results.png   # Screenshot kết quả pytest
├── production_readiness.png  # Screenshot readiness score
└── README.md                # Hướng dẫn setup
```

## Địa Điểm Nộp
Nộp link repo GitHub qua LMS

## Tiêu Chí Chấm Điểm

| Tiêu Chí | Trọng Số | Mô Tả |
|----------|----------|-------|
| Integration Completeness | 40% | Tất cả 10 integration points hoạt động, data flow end-to-end |
| Observability | 25% | Logs, metrics, traces hiển thị; alerts configured |
| Performance | 20% | Latency trong SLO; load tested; không có memory leaks |
| Architecture Quality | 15% | Clean separation, GitOps config, documented decisions |

## Các Vấn Đề Cần Tránh

- Config drift giữa các environments
- Thiếu error handling tại integration points
- Monitoring coverage không hoàn chỉnh
- Không có rollback strategy
- Demo không test trước khi nộp

## 5 Câu Hỏi Cần Trả Lời Khi Nộp

### 1. Phân tích các trade-offs trong thiết kế kiến trúc AI platform của bạn. Bạn đã cân bằng giữa performance, reliability, và maintainability như thế nào?

- **Trade-off (Sự đánh đổi):** Thiết kế kiến trúc Hybrid (Local Stack + Kaggle GPU serving) mang lại ưu thế lớn về chi phí (không cần tài nguyên GPU đắt đỏ ở local) nhưng đổi lại là độ trễ mạng (network latency) cao hơn do phải đi qua các kết nối tunnel (ngrok/cloudflare) tới Kaggle.
- **Cân bằng các tiêu chí:**
  - **Performance (Hiệu năng):** Chúng ta sử dụng Feast (Redis) làm Online Feature Store và Qdrant làm Vector Database trực tiếp ở Local. Nhờ vậy, quá trình tìm kiếm vector tương đồng và trích xuất đặc trưng (feature retrieval) diễn ra với độ trễ cực thấp (sub-millisecond), giảm số lần phải gọi trực tiếp sang dịch vụ Kaggle.
  - **Reliability (Độ tin cậy):** Đặt Kafka làm hàng đợi thông điệp ở đầu nguồn giúp đệm (buffer) dữ liệu. Nếu Prefect worker hoặc các thành phần lưu trữ ở local bị gián đoạn hoạt động, dữ liệu từ Producer vẫn được xếp hàng an toàn trên Kafka và tự động xử lý tiếp khi hệ thống phục hồi (không gây mất dữ liệu).
  - **Maintainability (Khả năng bảo trì):** Toàn bộ các dịch vụ local được đóng gói trong một file `docker-compose.yml` duy nhất. Việc tách biệt rõ ràng các nhiệm vụ (API Gateway lo serving/routing, Prefect lo ETL pipeline, Qdrant lo vector search, Feast lo feature caching) giúp dễ dàng mở rộng, thay thế hoặc nâng cấp riêng lẻ từng thành phần.

---

### 2. Trong kiến trúc hybrid (Local + Kaggle), bạn xử lý ngắt kết nối giữa local và Kaggle như thế nào? Có cơ chế fallback không?

- **Xử lý ngắt kết nối:** Tại API Gateway (`api-gateway/main.py`), chúng ta thiết lập cơ chế kiểm soát timeout (ở đây là 30 giây) khi kết nối với vLLM thông qua HTTPX client:
  ```python
  async with httpx.AsyncClient(timeout=30) as client:
      llm_resp = await client.post(...)
  ```
- **Cơ chế Fallback:**
  - Nếu kết nối tới vLLM bị lỗi hoặc timeout, API Gateway sẽ bắt exception và trả về kết quả fallback mặc định hoặc kết quả đã được cache sẵn trong Feature Store (Feast/Redis).
  - Đối với môi trường Production thực tế, cơ chế **Circuit Breaker** (như thư viện `pybreaker`) có thể được cấu hình ở API Gateway để tự động ngắt (trip) các yêu cầu tới Kaggle khi phát hiện lỗi liên tục, đồng thời định tuyến nhanh sang luồng fallback để hệ thống không bị treo nghẽn luồng.

---

### 3. Giải thích cách event-driven architecture với Kafka giúp decouple các components trong AI platform của bạn.

- **Mức độ Decouple (Tách biệt liên kết):**
  - **Temporal Decoupling (Tách biệt thời gian):** Producer (ví dụ: `scripts/01_ingest_to_kafka.py`) có thể chạy và ghi dữ liệu bất cứ lúc nào mà không cần biết Consumer (Prefect Pipeline) có đang chạy hay không.
  - **Spatial Decoupling (Tách biệt không gian):** API Gateway và Vector Store không cần gọi trực tiếp tới Prefect. Dữ liệu thô chỉ cần đi qua Kafka, giúp giảm thiểu sự phụ thuộc trực tiếp (tight-coupling) giữa các REST API.
- **Xử lý Backpressure:** Khi lưu lượng dữ liệu tăng đột biến (peak traffic), Kafka lưu trữ tạm thời các tin nhắn trong phân vùng topic (`data.raw`). Prefect Pipeline sẽ consume theo tốc độ xử lý định mức của nó (pull-based), tránh hiện tượng sập hệ thống do quá tải đột ngột.

---

### 4. Bạn đã implement observability như thế nào? Logs, metrics, và traces được thu thập và visualized ra sao?

- **Metrics:**
  - API Gateway sử dụng thư viện `prometheus-fastapi-instrumentator` để tự động thu thập và expose metrics hiệu năng của API (latency, requests count, status codes) tại endpoint `/metrics`.
  - Prometheus chạy định kỳ scrape metrics từ API Gateway, Kafka và Prefect Orion.
  - Grafana được kết nối làm giao diện trực quan hóa dữ liệu từ Prometheus thông qua các Dashboard giám sát thời gian thực (được cấu hình qua cổng `3000`).
- **Logs:** Toàn bộ stdout/stderr của các container được quản lý tập trung bởi Docker daemon, cho phép xem nhanh thông qua lệnh `docker compose logs <service>`.
- **Traces:** Giao thức LangSmith được tích hợp thông qua cấu hình môi trường để theo dõi chi tiết luồng gọi LLM (prompts, responses, tokens count và execution time).

---

### 5. Nếu một service trong stack (ví dụ: Qdrant hoặc Kafka) bị crash, hệ thống của bạn sẽ xử lý như thế nào? Có graceful degradation không?

- **Nếu Kafka bị crash:**
  - Ingestion Script (Producer) sẽ thử kết nối lại hoặc lưu đệm dữ liệu vào file cục bộ trên host.
  - Prefect worker sẽ ghi nhận lỗi kết nối tới Kafka nhưng không bị dừng đột ngột; worker vẫn online và liên tục thăm dò để tự động chạy lại flow khi Kafka khả dụng trở lại.
- **Nếu Qdrant (Vector Store) bị crash:**
  - API Gateway khi thực hiện tìm kiếm ngữ cảnh (vector search) sẽ gặp lỗi kết nối. Tuy nhiên, thay vì sập hoàn toàn (trả về lỗi 500), API Gateway sẽ thực hiện **Graceful Degradation (Suy giảm chức năng mềm dẻo)**:
    - Bắt exception của thư viện tìm kiếm vector.
    - Chuyển sang luồng LLM inference không có ngữ cảnh tương đồng (no-context fallback) hoặc sử dụng static prompt để trả về kết quả tối thiểu cho người dùng.
    - Trả về thông báo lỗi thân thiện thay vì làm đứt gãy trải nghiệm của client.

---

## Kết quả nghiệm thu thực tế (Verification Summary)

Toàn bộ các yêu cầu của sprint đã được kiểm thử và hoàn thành xuất sắc tại môi trường local:

1. **Kết quả Smoke Tests (`pytest smoke-tests/ -v`)**:
   - Hoàn thành **8/8 test cases PASSED** (bao gồm Happy Path, Data Ingestion, Observability, Error Handling, và Feature Store).
2. **Production Readiness Score**:
   - Đạt điểm tối đa **10/10 (100% READY)**.
3. **Observability Verification**:
   - Tích hợp thành công luồng Prometheus và xử lý lỗi LangSmith khi thiếu API Key.
4. **Git Version Control**:
   - Đã cập nhật `.gitignore` để loại bỏ thư mục dữ liệu chạy thực tế `delta-lake/`.
   - Đã thực hiện commit chia nhỏ 5 phần và push thành công lên GitHub repository main branch.

---
## Hướng Dẫn Setup & Start Platform Nhanh
```bash
# 1. Clone repo và sao chép cấu hình môi trường
cp .env.example .env # Đã có sẵn cấu hình local mock-server

# 2. Khởi động Docker Compose local stack (bao gồm cả Mock vLLM & Embed Server)
docker compose up -d --build

# 3. Deploy Prefect Pipeline (chạy bên trong worker container)
docker exec day28-2a202600723-nguyenthivang-lab-assignment-prefect-worker-1 python /opt/prefect/flows/kafka_to_delta.py

# 4. Chạy luồng tích hợp dữ liệu
python scripts/01_ingest_to_kafka.py # Ingest raw data to Kafka
docker exec day28-2a202600723-nguyenthivang-lab-assignment-prefect-worker-1 prefect deployment run "Kafka to Delta Pipeline/kafka-to-delta" # Trigger Prefect flow
python scripts/03_delta_to_feast.py # Delta to Feast (Redis)
python scripts/05_embed_to_qdrant.py # Embed to Qdrant (Vector Store)

# 5. Chạy kiểm thử tự động
pytest smoke-tests/ -v
python scripts/production_readiness_check.py
```


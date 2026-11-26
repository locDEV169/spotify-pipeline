# Data model layers — `raw_charts` vs `fact_chart` (và vì sao không có `dim_chart`)

**Audience:** onboarding / portfolio explain  
**Status:** mirrors current DDL + SPEC (medallion Bronze → Silver → Gold)  
**Canonical DDL:** [`docs/sql/init/music_schema.sql`](../sql/init/music_schema.sql)  
**Canonical SPEC:** [`SPEC.md`](SPEC.md) — Data model (Silver) + medallion mapping

---

## 1. Tóm tắt nhanh

| Object | Layer | Vai trò một câu |
|--------|-------|-----------------|
| `music.raw_charts` | Bronze | Giữ **payload JSON thô** từ Charts API (1 lần ingest ≈ 1 row) |
| `music.fact_chart` | Silver | Bảng **xếp hạng đã chuẩn hóa** (1 track trên 1 watermark = 1 row) |
| `music.dim_track` | Silver | Hồ sơ bài hát (metadata Spotify + features ReccoBeats) |
| `music.dim_artist` | Silver | Hồ sơ nghệ sĩ |
| `music.dim_chart` | — | **Không tồn tại** trong repo này |

Tên đúng là **`raw_charts`** (số nhiều), không phải `raw_chart`.

---

## 2. Vì sao có cả Bronze và Silver?

Pipeline theo **medallion**:

```text
Charts API
   → Bronze  music.raw_charts     (raw JSON, audit / reprocess)
   → Silver  music.fact_chart     (curated ranks)
             + dim_track / dim_artist
   → Gold    VIEW (coverage / movers / mood)
```

Hai bảng chart không trùng chức năng:

1. **`raw_charts`** — “camera roll”: giữ nguyên response nguồn + `ingested_at` / `run_id`.
2. **`fact_chart`** — “bảng xếp hạng đã cắt khung”: cột nghiệp vụ (`rank`, `prev_rank`, `track_id`, …), PK ổn định để upsert / join.

### Lợi ích thiết kế (đã lock trong SPEC)

- **Tái chạy Silver** từ Bronze mà **không** gọi Charts lại.
- **Không mất field** chưa model — JSON còn trong `payload`.
- **Idempotent:** Bronze append theo lần ingest; Silver upsert theo PK.
- **LEFT JOIN rule (BR-6):** hàng chart sống ở `fact_chart` dù `dim_track.features_found = false`.

---

## 3. So sánh chi tiết

### `music.raw_charts` (Bronze)

| Khía cạnh | Giá trị |
|-----------|---------|
| Grain | ~1 row = 1 lần ingest (cả chart nằm trong `payload jsonb`) |
| PK | `id` (identity) |
| Cột chính | `source`, watermark hints (`chart_date`, `chart_type`, `country`), `payload`, `ingested_at`, `run_id` |
| Ai đọc | `extract_ids`, `build-silver` (parse JSON → curated tables) |
| Không dùng để | Báo cáo Gold trực tiếp / analytics hạng |

Happy path enrich: lấy track IDs từ **latest** `raw_charts` theo watermark — không re-fetch Charts trên path đó.

### `music.fact_chart` (Silver)

| Khía cạnh | Giá trị |
|-----------|---------|
| Grain | 1 row = 1 `(chart_date, chart_type, country, track_id)` |
| PK | `(chart_date, chart_type, country, track_id)` |
| Cột chính | `rank`, `prev_rank`, `streams` (NULL trên `public/v0`), `entry_status`, … |
| Ai đọc | Gold VIEWs, analytics (movers / coverage) |
| Build | `build-silver` parse Bronze → `INSERT … ON CONFLICT` |

---

## 4. Star schema trong project này

```text
                    ┌─────────────┐
                    │ dim_artist  │
                    └──────┬──────┘
                           │ M:N
                    ┌──────┴──────┐
   fact_chart ─────►│ dim_track   │◄── features / metadata
   (ranks)          └─────────────┘
```

- **Fact** = sự kiện đo được: *track X xếp hạng #N trên chart Y ngày Z*.
- **Dim** = thuộc tính mô tả entity tái sử dụng được (`track`, `artist`).

Gold (ví dụ movers / coverage) luôn đi từ `fact_chart` **LEFT JOIN** `dim_track` — thiếu features **không** xóa hàng chart.

Runtime template: [`docs/sql/silver/silver_fact_chart_left_join_dim_track.sql`](../sql/silver/silver_fact_chart_left_join_dim_track.sql).

---

## 5. `dim_chart` — có cần không?

### Fact

- Toàn repo **không** định nghĩa / tạo `dim_chart`.
- SPEC Data model chỉ liệt kê: `fact_chart`, `dim_track`, `dim_artist` (+ bridge).

### Vì sao watermark không tách thành `dim_chart`?

Watermark hiện chỉ gồm ba thuộc tính đơn giản:

- `chart_date`
- `chart_type` (MVP: `weekly_top_songs`)
- `country` (MVP: `global`)

Chúng **đã nằm trong grain / PK của `fact_chart`**. Tách bảng `dim_chart` lúc này chưa earn complexity (YAGNI) vì MVP gần như một chart cố định.

### Khi nào *có thể* cân nhắc thêm `dim_chart`?

Chỉ khi xuất hiện nhu cầu thật, ví dụ:

- Nhiều chart type / region song song cần label, timezone, timezone-aware “week start”
- Metadata định nghĩa chart (display name, source endpoint, auth mode) tái dùng nhiều fact
- Surrogate `chart_key` thay vì lặp 3 cột trên mọi fact

Cho đến khi đó: **giữ watermark trên `fact_chart`**.

---

## 6. Ví dụ đọc đúng lớp

| Câu hỏi | Đọc bảng |
|---------|----------|
| Payload Charts lần ingest gần nhất? | `raw_charts` |
| Track #1 tuần này là ID nào, `prev_rank` bao nhiêu? | `fact_chart` |
| Bài đó danceability / `features_found`? | `dim_track` (join từ fact) |
| % coverage features của watermark? | Gold VIEW `gold_feature_coverage` (fact LEFT JOIN dim) |

**Tránh:** parse Gold từ `raw_charts.payload` mỗi lần — bypass Silver → khó idempotent và dễ lệch BR-6.

---

## 7. Liên kết code / ops

| Việc | Entry |
|------|--------|
| DDL | `docs/sql/init/music_schema.sql` |
| Load Bronze charts | `python scripts/bronze/load_raw_charts.py` |
| Build Silver (gồm fact) | `python -m spotify_pipeline build-silver --chart-date …` |
| Build Gold | `python -m spotify_pipeline build-gold --chart-date …` |
| Gaps / checklist | [`CHECKLIST_SPEC_GAPS.md`](CHECKLIST_SPEC_GAPS.md) |

---

## 8. Quyết định giữ nguyên (không đổi schema)

| Quyết định | Lý do ngắn |
|------------|------------|
| Giữ `raw_charts` + `fact_chart` | Tách raw vs curated (medallion) |
| Không tạo `dim_chart` (MVP) | Watermark đủ nhỏ; nằm trong PK fact |
| Features trên `dim_track`, không trên fact | Cùng track xuất hiện nhiều watermark; LEFT JOIN + `features_found` |

# 🛡️ CyberGuard Backend V2 — Final Complete

## المميزات الكاملة

| النظام | الوصف |
|--------|-------|
| 17 طبقة ذكاء | Pipeline كامل |
| Neural Knowledge Engine | خلايا + معرفة + استنتاج |
| Cell Evolution System | تفرع تلقائي |
| Knowledge Graph | شبكة العلاقات |
| Knowledge Sandbox | تحقق قبل القبول |
| Discovery Engine | استنتاج ذاتي |
| Reward/Punishment | مكافأة متعددة المصادر |
| File Scanner | YARA + IOC + Entropy |
| WebSocket Dashboard | أحداث حية |

---

## التشغيل

```bash
pip install -r requirements.txt
cp .env.example .env
# عدّل .env
python main.py
```

---

## API Endpoints

### Auth
```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
```

### Analysis
```
POST /api/v1/analyze
POST /api/v1/analyze/url
POST /api/v1/analyze/hash
POST /api/v1/analyze/rate
GET  /api/v1/analyze/result/{key}
```

### Scanner
```
POST /api/v1/scan/upload
GET  /api/v1/scan/{scan_id}
GET  /api/v1/scan/user/history
```

### Dashboard
```
GET  /api/v1/dashboard/health
GET  /api/v1/dashboard/stats
GET  /api/v1/dashboard/cells
GET  /api/v1/dashboard/cells/graph
GET  /api/v1/dashboard/hypotheses
GET  /api/v1/dashboard/heatmap
GET  /api/v1/dashboard/timeline
GET  /api/v1/dashboard/learning
GET  /api/v1/dashboard/knowledge/sandbox
WS   /api/v1/dashboard/ws/stats
WS   /api/v1/dashboard/ws/neural
```

### Admin
```
POST /api/v1/admin/train
GET  /api/v1/admin/stats
POST /api/v1/admin/ban
GET  /api/v1/admin/users
GET  /api/v1/admin/logs
GET  /api/v1/admin/cells
POST /api/v1/admin/cells/retire
GET  /api/v1/admin/hypotheses
POST /api/v1/admin/sandbox/process
```

### System
```
GET  /         → معلومات
GET  /health   → UptimeRobot
GET  /ping     → Lightweight ping
GET  /docs     → Swagger UI
GET  /redoc    → ReDoc
```

---

## WebSocket Events

```json
{"event": "CELL_CREATED"}
{"event": "CELL_SPECIALIZED"}
{"event": "CELL_RETIRED"}
{"event": "KNOWLEDGE_ADDED"}
{"event": "CONNECTION_CREATED"}
{"event": "DISCOVERY_MADE"}
{"event": "CONFIDENCE_UPDATED"}
{"event": "SNAPSHOT"}
{"event": "STATS_UPDATE"}
```

---

## الرفع على Render

1. ارفع على GitHub
2. New → Web Service
3. أضف متغيرات `.env.example`
4. Deploy ✅
5. أضف `/ping` في UptimeRobot كل 5 دقائق

---

## MongoDB Collections

```
users              → المستخدمون
knowledge          → المعرفة المتحقق منها
knowledge_sandbox  → معرفة قيد التحقق
ratings            → تقييمات المستخدمين
cells              → الخلايا المعرفية
hypotheses         → الفرضيات والاستنتاجات
reward_logs        → سجل المكافآت والعقوبات
scans              → نتائج فحص الملفات
logs               → سجلات النظام
```

# 🛡️ CyberGuard Backend V2

## التثبيت والتشغيل

```bash
# 1. تثبيت المكتبات
pip install -r requirements.txt

# 2. إعداد البيئة
cp .env.example .env
# عدّل القيم في .env

# 3. تشغيل السيرفر
python main.py
```

## API Endpoints

| Method | Endpoint | الوظيفة |
|--------|----------|---------|
| POST | /api/v1/auth/register | تسجيل |
| POST | /api/v1/auth/login | دخول |
| POST | /api/v1/analyze | تحليل نصي |
| POST | /api/v1/analyze/url | تحليل رابط |
| POST | /api/v1/analyze/rate | تقييم نتيجة |
| POST | /api/v1/scan/upload | رفع ملف |
| GET  | /api/v1/scan/{id} | نتيجة فحص |
| GET  | /api/v1/dashboard/health | صحة النظام |
| WS   | /api/v1/dashboard/ws/stats | إحصائيات مباشرة |
| GET  | /health | UptimeRobot |
| GET  | /ping | Lightweight ping |
| GET  | /docs | Swagger UI |

## الرفع على Render

1. ارفع الكود على GitHub
2. اربطه بـ Render Web Service
3. أضف متغيرات البيئة من render.yaml
4. اربط /ping بـ UptimeRobot كل 5 دقائق

## MongoDB Atlas

1. أنشئ Cluster مجاني على mongodb.com
2. أضف MONGODB_URI في .env

# 🗓️ Sprint Plan — תכנית עבודה שבועית

הטבלה מפרטת מה ייעשה כל שבוע. כל שבוע כולל **תוצר ברור** — לא "עובדים על...", אלא "סיימנו X".

---

| שבוע | תאריך | יעד | תוצר מצופה | M |
|:----:|:-----:|-----|------------|:-:|
| **3** | 09/04 | **README + Skeleton + Sprint Plan** | כל קבצי M1 מוכנים: README מלא עם ארכיטקטורה ו-DB schema, Sprint Plan שבועי, Skeleton פרויקט (תיקיות + package.json + Docker Compose) | **M1** |
| **4** | 16/04 | בסיס נתונים + אימות + CRUD | PostgreSQL + PostGIS רץ ב-Docker, סכמת Prisma מלאה, Seed עם נתוני דוגמה, מערכת Login/JWT, API ל-CRUD פרויקטים ולקוחות עובד (Postman collection) | |
| **5** | 23/04 | **Google Earth API — מפה ראשונה + העלאת קבצים** | ממשק React עם Google Earth מציג פרויקטים כ-KML Markers, העלאת קבצי DXF/CSV/DWG, חילוץ גאומטריות והצגה על המפה | **M2** |
| **6** | 30/04 | חיפוש מרחבי + סינון + שיפור UI | חיפוש מרחבי (ציור אזור → שליפת מדידות), סינון לפי תאריכים/סוג מדידה/סטטוס, Dashboard עם סטטיסטיקות, ממשק מלוטש (Sidebar + ניווט) | |
| **7** | 07/05 | אינטגרציה Google Sheets + Validation | חיבור ל-Google Sheets API, קריאת יומן עבודות והצגה על Google Earth, סנכרון דו-כיווני, Validation מלא בצד שרת ולקוח | |
| **8** | 14/05 | **Deploy + פרסום** | URL ציבורי פעיל, המערכת פרוסה ב-Docker, הרשאות RBAC (Admin/Manager/Surveyor), PWA ניתנת להתקנה, SSL מוגדר | **M3** |
| **9** | 28/05 | מרתון פיתוח — שיפורים | הפקת דוחות PDF, ייצוא ל-KMZ/DXF/SHP, תמיכה ב-Shapefile + GeoJSON + KML, חיפוש לפי גוש/חלקה, תיקון באגים, אופטימיזציה | |
| **10** | 11/06 | 🎓 **Demo Day** | הצגה חיה בפני הכיתה: מפת Google Earth עם מדידות, חיפוש מרחבי, סנכרון יומן עבודות Google Sheets, Dashboard, גרסה סופית יציבה | **סופי** |

---

## 📌 Milestones — אבני דרך

| M | שם | תאריך | תוצר נדרש |
|:-:|-----|:-----:|-----------|
| **M1** | הגדרה ותכנון | 09/04 | README מלא + Sprint Plan + Skeleton פרויקט |
| **M2** | מודל עובד + תוצאה ראשונה | 23/04 | Google Earth API מציג פרויקטים על המפה, העלאת קבצים + חילוץ גאומטריות |
| **M3** | Deploy + פרסום | 14/05 | URL ציבורי פעיל, מערכת מלאה עם Google Sheets, הרשאות, PWA |
| **סופי** | Demo Day | 11/06 | הצגה חיה בפני הכיתה — גרסה יציבה ומלוטשת |

---

## 📋 פירוט שבועי

### שבוע 3 (09/04) — M1: README + Skeleton + Sprint Plan

- [x] כתיבת README מפורט עם ארכיטקטורה, DB schema, API
- [x] הגדרת Google Earth כממשק המפה (אבטחת מידע + Google Sheets)
- [x] כתיבת Sprint Plan שבועי
- [ ] אתחול פרויקט: `client/` (Vite + React + TS) + `server/` (Python + Flask)
- [ ] הגדרת Docker Compose (PostgreSQL + PostGIS + Redis)
- [ ] הגדרת `.env.example` עם כל המשתנים
- [ ] יצירת `requirements.txt` + `app.py`
- [ ] Push ל-GitHub

### שבוע 4 (16/04) — בסיס נתונים + אימות + CRUD

- [ ] כתיבת מודלים SQLAlchemy + GeoAlchemy2 (users, clients, projects, survey_types, survey_files, geo_features)
- [ ] הפעלת PostGIS extension
- [ ] הרצת מיגרציה ראשונה (Alembic)
- [ ] כתיבת Seed — נתוני דוגמה (5 פרויקטים, 3 משתמשים, 3 לקוחות)
- [ ] מערכת הרשמה/כניסה (Flask-JWT-Extended + bcrypt)
- [ ] אימות Google Workspace (OAuth2)
- [ ] Middleware להרשאות RBAC (admin/manager/surveyor)
- [ ] API: CRUD פרויקטים (GET/POST/PUT/DELETE)
- [ ] API: CRUD לקוחות
- [ ] Postman Collection מוכנה לבדיקות

### שבוע 5 (23/04) — M2: Google Earth API + העלאת קבצים

- [ ] הגדרת Google Earth API key
- [ ] רכיב React: מפת Google Earth אינטראקטיבית
- [ ] שליפת פרויקטים מ-API והצגה כ-KML Markers
- [ ] Popup/Info Window בלחיצה על מרקר (שם, סטטוס, תאריך, לקוח)
- [ ] Layout: Header + Sidebar + Map
- [ ] ממשק העלאה (React-Dropzone) עם Drag & Drop
- [ ] Parser ל-DXF: חילוץ שכבות, נקודות, קווים, פוליגונים
- [ ] Parser ל-CSV: יצירת נקודות מ-X,Y,Z
- [ ] המרת קואורדינטות ל-WGS84 (Proj4js) להצגה ב-Google Earth
- [ ] שמירת geo_features ב-DB + הצגה על המפה

### שבוע 6 (30/04) — חיפוש מרחבי + סינון + UI

- [ ] כלי ציור על המפה (מלבן/עיגול/פוליגון)
- [ ] API: `POST /api/search/spatial` — חיפוש PostGIS
- [ ] סינון לפי טווח תאריכים (date picker)
- [ ] סינון לפי סוג מדידה (dropdown)
- [ ] סינון משולב (אזור + תאריכים + סוג)
- [ ] תוצאות: רשימה + הדגשה על המפה
- [ ] Dashboard ראשי עם סטטיסטיקות (כרטיסיות KPI + גרפים)
- [ ] שיפור ממשק: ניווט, Sidebar, Responsive Design

### שבוע 7 (07/05) — Google Sheets + Validation

- [ ] הגדרת Google Service Account
- [ ] חיבור ל-Google Sheets API (googleapis)
- [ ] קריאת יומן עבודות קיים מה-Sheet
- [ ] הצגת עבודות מהיומן כשכבה על Google Earth
- [ ] סנכרון: יצירת פרויקט במערכת → שורה חדשה ב-Sheet
- [ ] סנכרון: עדכון סטטוס ב-Sheet → עדכון במערכת
- [ ] Validation: Marshmallow / Pydantic בכל API endpoints
- [ ] Error handling מרוכז (middleware)
- [ ] Loading states + Error states ב-UI

### שבוע 8 (14/05) — M3: Deploy + פרסום

- [ ] Build: Docker images (client + server)
- [ ] Deploy לשרת (VPS / Cloud Run / Railway)
- [ ] הגדרת SSL (HTTPS)
- [ ] הגדרת Domain / URL ציבורי
- [ ] הרשאות RBAC פועלות (Admin/Manager/Surveyor)
- [ ] PWA: manifest.json + Service Worker
- [ ] בדיקת המערכת בטלפון נייד
- [ ] בדיקות E2E: תהליך מלא מקצה לקצה

### שבוע 9 (28/05) — מרתון פיתוח — שיפורים

- [ ] הפקת דוח PDF (סיכום פרויקט)
- [ ] ייצוא נתונים ל-KMZ / DXF / SHP / CSV
- [ ] תמיכה בייבוא Shapefile + GeoJSON + KML
- [ ] חיפוש לפי גוש/חלקה
- [ ] חיפוש לפי כתובת (Google Geocoding API)
- [ ] שיפורי ביצועים (Clustering, Lazy loading)
- [ ] תיעוד API (Swagger / OpenAPI)
- [ ] תיקון באגים אחרונים

### שבוע 10 (11/06) — סופי: Demo Day 🎓

- [ ] הכנת תסריט הצגה (Demo Script)
- [ ] הכנת מצגת
- [ ] Dry run — הרצה מלאה של ההצגה
- [ ] **הצגה חיה בפני הכיתה** 🎉
- [ ] תיעוד סופי
- [ ] הגשת קוד סופי ל-GitHub

---

<div align="center">
<sub>SurveyGIS Sprint Plan — אפריל–יוני 2026</sub>
</div>

# 🌍 SurveyGIS — מערכת GIS פנים-משרדית לניהול מדידות
**מגישים: בר שפילמן ונעמה הקשר**
<div align="center">

**מערכת מידע גאוגרפי מבוססת Google Earth** 
**לניהול, שליפה והצגת מדידות במשרד מדידות**

🔗 **[למעבר לאפליקציית חקר הנתונים (Streamlit) לחץ כאן](https://ha6xlpm9d2ay7ku5ez6vvo.streamlit.app/)** 🔗




`v1.0.0` · אפריל 2026

</div>

---

## 📑 תוכן עניינים

1. [סקירה כללית](#-סקירה-כללית)
2. [אפליקציית ניתוח הנתונים EDA](#-אפליקציית-ניתוח-הנתונים-eda)
3. [בעיה ופתרון](#-בעיה-ופתרון)
4. [משתמשי המערכת](#-משתמשי-המערכת)
5. [ארכיטקטורה](#-ארכיטקטורה)
6. [קלט — סוגי קבצים ומקורות מידע](#-קלט--סוגי-קבצים-ומקורות-מידע)
7. [פלט — תוצרים ודוחות](#-פלט--תוצרים-ודוחות)
8. [בסיס נתונים](#-בסיס-נתונים)
9. [מנוע מפות — Google Earth](#-מנוע-מפות--google-earth)
10. [API — ממשק תכנות](#-api--ממשק-תכנות)
11. [טכנולוגיות](#-טכנולוגיות)
12. [התקנה והרצה](#-התקנה-והרצה)
13. [תהליכי עבודה](#-תהליכי-עבודה)
14. [אבטחה והרשאות](#-אבטחה-והרשאות)
15. [Roadmap — תכנית פיתוח](#-roadmap--תכנית-פיתוח)

---

## 📊 אפליקציית ניתוח הנתונים EDA

🔗 **[לאפליקציה החיה לחצי כאן](https://ha6xlpm9d2ay7ku5ez6vvo.streamlit.app/)**

אפליקציית **SurveyGIS EDA** בנויה על **Streamlit** ומאפשרת ניתוח וחקר נתוני מדידות בצורה אינטראקטיבית — ללא צורך בקוד.

### שימוש באפליקציה

![מסך הסקירה הכללית של אפליקציית EDA](images/eda_screenshot.png)

#### שלבי העבודה

| שלב | פעולה | תיאור |
|-----|--------|--------|
| 1️⃣ | **העלאת קובץ CSV** | לחצי על "Upload" בסרגל הצד והעלי קובץ נתוני מדידות |
| 2️⃣ | **סקירה כללית** | צפי בסטטיסטיקות בסיסיות — מספר שורות, עמודות, ערכים חסרים |
| 3️⃣ | **קיבוץ** | ניתוח קיבוצי (Clustering) לזיהוי דפוסים בנתוני מדידה |
| 4️⃣ | **אודות** | מידע על האפליקציה |

#### יכולות מרכזיות

- **סקירת מערכת הנתונים** — מספר שורות, עמודות, עמודות מספריות, ו-% ערכים חסרים
- **תצוגה מקדימה** של הנתונים הגולמיים
- **ניתוח סטטיסטי** — חישוב ממוצעים, סטיות תקן, מינימום ומקסימום
- **קיבוץ (Clustering)** — זיהוי קבוצות בנתוני המדידות באמצעות KMeans
- **וויזואליזציות** — גרפים אינטראקטיביים מבוססי Plotly

#### הרצה מקומית

```bash
cd dwg_to_csv
streamlit run eda_app.py
```

---

## 🔭 סקירה כללית

**SurveyGIS** היא מערכת GIS פנים-משרדית המיועדת למשרד מדידות, המבוססת על **Google Earth** כממשק המפה המרכזי.

### 🌐 למה Google Earth?

| סיבה | הסבר |
|-------|-------|
| 🔒 **אבטחת מידע** | Google Earth מציע תשתית אבטחה מתקדמת ברמה ארגונית (Google Workspace), כולל הצפנה, ניהול הרשאות, ואימות דו-שלבי — קריטי עבור מידע מדידות רגיש |
| 📊 **אינטגרציה עם Google Sheets** | במשרד כבר קיים **יומן עבודות פעיל המתומשך ל-Google Sheets**. שימוש ב-Google Earth מאפשר אינטגרציה טבעית וחלקה עם יומן העבודות הקיים, ללא צורך בהעברת נתונים או מערכות מקבילות |
| 🔗 **אקוסיסטם אחוד** | עבודה בתוך אקוסיסטם Google (Earth + Sheets + Drive) מבטיחה תאימות מלאה, ניהול הרשאות מרוכז, ושיתוף פעולה חלק בין כל רכיבי המערכת |

המערכת מאפשרת:

- **העלאת קבצי מדידה** (DWG, DXF, SHP, CSV, KML/KMZ ועוד) וחיבורם למיקום גאוגרפי על Google Earth.
- **חיפוש מרחבי** — לחיצה על מיקום במפה ושליפת כל המדידות שנעשו באזור.
- **סינון וחיפוש** — סינון מדידות לפי **טווח תאריכים**, **סוג מדידה**, אזור גאוגרפי, סטטוס ועוד.
- **ניהול פרויקטים** — מעקב אחרי סטטוס פרויקטים, לקוחות, ומודדים אחראיים.
- **סנכרון עם יומן עבודות** — חיבור ישיר ל-Google Sheets לעדכון אוטומטי של יומן העבודות המשרדי.
- **גישה מהשטח** — מודדים בשטח יכולים **לצפות** במדידות קיימות ולהוריד חומרים רלוונטיים (ללא העלאת קבצים).
- **הפקת דוחות** — ייצוא מפות, סיכומי פרויקטים וניתוחים סטטיסטיים.

       ---

## 🎯 בעיה ופתרון

### הבעיה

| כאב | תיאור |
|------|--------|
| 🔍 קושי בשליפה | קבצי מדידה מפוזרים בתיקיות שונות במחשב למי מספרי עבודה מרובים, קשה למצוא מדידה ישנה |
| 🗺️ חוסר תמונה מרחבית | אין מפה אחודה שמראה איפה בוצעו מדידות בעבר |
| 📂 כפילויות | מדידות חוזרות באותו אזור בלי לדעת שכבר קיים מידע |
| 📊 חוסר מעקב | קשה לעקוב אחרי סטטוס פרויקטים, לקוחות, וחשבוניות |
| 📱 גישה מהשטח | מודדים בשטח לא יכולים לגשת למידע ההיסטורי |

### הפתרון

מערכת GIS אחודה מבוססת **Google Earth** שמרכזת את **כל קבצי המדידה** על **מפה אינטראקטיבית**, עם **חיפוש מרחבי**, **ניהול פרויקטים**, **סנכרון עם יומן עבודות ב-Google Sheets**, ו**גישה ניידת** מהשטח. הבחירה ב-Google Earth נובעת מדרישות **אבטחת מידע** ומהאינטגרציה הטבעית עם **Google Sheets** בו מנוהל יומן העבודות המשרדי.

---

## 👥 משתמשי המערכת

### 1. מנהל פרויקט (Project Manager)

| פעולה | תיאור |
|-------|--------|
| ניהול פרויקטים | יצירת פרויקטים, הקצאת מודדים, מעקב סטטוס |
| חיפוש מרחבי | חיפוש מדידות לפי אזור גאוגרפי, חלקה, גוש |
| הפקת דוחות | ייצוא סיכומים, מפות, וסטטיסטיקות |
| ניהול לקוחות | ריכוז פרטי לקוחות וקישור לפרויקטים |
| העלאת קבצים | העלאת תוכניות, מפות ותוצרי מדידה |
| צפייה בהיסטוריה | צפייה בכל המדידות שבוצעו באזור מסוים |

### 2. מודד בשטח (Field Surveyor)

> ⚠️ **הערה:** מודדים בשטח **אינם מעלים קבצים** למערכת. העלאת קבצים (מפות סופיות בלבד) מתבצעת ע"י מנהל פרויקט או מנהל מערכת.

| פעולה | תיאור |
|-------|--------|
| צפייה במפה | צפייה בגבולות מדידות קיימות ובנקודות קואורדינטה |
| סינון מדידות | סינון לפי תאריכים, סוג מדידה, אזור, וסטטוס |
| דיווח סטטוס | עדכון התקדמות עבודה בשטח |
| הורדת קבצים | הורדת חומרים רלוונטיים למדידה (תוכניות, מפות ישנות) |
| ניווט | ניווט לנקודת המדידה ע"פ קואורדינטות |

### 3. מנהל מערכת (Admin)

| פעולה | תיאור |
|-------|--------|
| ניהול משתמשים | הוספה/עריכה/מחיקת משתמשים והרשאות |
| הגדרות מערכת | ניהול שכבות מפה, מערכות קואורדינטות, תבניות |
| גיבוי ושחזור | ניהול גיבויים ושחזור נתונים |

---

## 🏗️ ארכיטקטורה

```
┌──────────────────────────────────────────────────────────┐
│                    לקוח (Client)                         │
│  ┌─────────────────┐     ┌─────────────────────────┐     │
│  │  אפליקציית Web  │     │  אפליקציה ניידת (PWA)   │     │
│  │  React + Google │     │  React + Google Earth   │     │
│  │  Earth API      │     │                         │     │
│  └────────┬────────┘     └───────────┬─────────────┘     │
└───────────┼──────────────────────────┼───────────────────┘
            │          HTTPS           │
            ▼                          ▼
┌──────────────────────────────────────────────────────────┐
│                    שרת (Server)                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │              Python / Flask                      │     │
│  │         REST API + WebSocket                     │     │
│  └────┬────────────────┬───────────────┬───────────┘     │
│       │                │               │                  │
│  ┌────▼───────────┐ ┌──▼────────────┐ ┌▼───────────────┐ │
│  │ File Processor │ │ Geo Service   │ │ Google Sheets  │ │
│  │ (DXF/SHP/CSV   │ │ (pyproj,      │ │ Sync Service   │ │
│  │  Parser)       │ │  Shapely)     │ │ (יומן עבודות)  │ │
│  └────────┬───────┘ └──────┬────────┘ └───────┬────────┘ │
└───────────┼────────────────┼──────────────────┼──────────┘
            │                │                  │
            ▼                ▼                  ▼
┌──────────────────────────────────────────────────────────┐
│                  בסיס נתונים (Database)                   │
│  ┌─────────────────────────────────────────────────┐     │
│  │         PostgreSQL + PostGIS                     │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐    │     │
│  │  │ Projects │ │ Surveys  │ │ GeoData      │    │     │
│  │  │          │ │          │ │ (Geometries) │    │     │
│  │  └──────────┘ └──────────┘ └──────────────┘    │     │
│  └─────────────────────────────────────────────────┘     │
│  ┌─────────────────┐  ┌────────────────────────────┐     │
│  │  אחסון קבצים    │  │  Google Sheets (יומן עבודות)│     │
│  │  MinIO / Local  │  │  ← סנכרון דו-כיווני        │     │
│  └─────────────────┘  └────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

---

## 📥 קלט — סוגי קבצים ומקורות מידע

### קבצי מדידה נתמכים

| פורמט | סיומת | תיאור | עיבוד |
|--------|--------|--------|--------|
| AutoCAD DWG | `.dwg` | קבצי שרטוט מ-AutoCAD / Civil3D (פורמט מקורי) | המרה ל-DXF ← חילוץ שכבות, גאומטריות, וקואורדינטות |
| AutoCAD DXF | `.dxf` | קבצי שרטוט בפורמט חליפין (Drawing Exchange) | חילוץ שכבות, גאומטריות, וקואורדינטות |
| Shapefile | `.shp` + `.dbf` + `.shx` + `.prj` | קבצי GIS סטנדרטיים | ייבוא ישיר לבסיס הנתונים |
| CSV / TXT | `.csv`, `.txt` | טבלאות קואורדינטות (X, Y, Z) | פרסור ויצירת נקודות/פוליגונים |
| GeoJSON | `.geojson` | פורמט גאוגרפי מבוסס JSON | ייבוא ישיר |
| LAS / LAZ | `.las`, `.laz` | ענני נקודות (Point Clouds) מסריקת לייזר | עיבוד וייצוג על המפה |
| KML / KMZ | `.kml`, `.kmz` | קבצי Google Earth | ייבוא ישיר ל-Google Earth |
| GPX | `.gpx` | מסלולי GPS | ייבוא נקודות ומסלולים |
| תמונות | `.jpg`, `.tif` | תמונות אורתופוטו / אווריות | הצגה כשכבת רקע |
| PDF | `.pdf` | תוכניות סרוקות | אחסון ושיוך לפרויקט |

> ⚠️ **חשוב:** מעלים למערכת **מפות סופיות בלבד** (לאחר עיבוד ובדיקה). העלאת קבצים מותרת למנהלי פרויקט ומנהלי מערכת בלבד.

### מקורות מידע נוספים

| מקור | תיאור |
|-------|--------|
| רשות מקרקעי ישראל | גבולות גושים וחלקות |
| מאגר ההסדר | מפות הסדר |
| המרכז למיפוי ישראל (MAPI) | שכבות רקע, מודלי גובה |
| טאבו / נסח | פרטי בעלות ורישום |
| רשויות מקומיות | תוכניות בנין עיר (תב"ע) |

### נתונים שמוזנים ידנית

| שדה | תיאור | דוגמה |
|------|--------|--------|
| שם פרויקט | שם תיאורי | "מדידה לפיצול חלקה — רמת גן" |
| לקוח | שם הלקוח / חברה | "חברת אלון בנייה בע\"מ" |
| גוש | מספר גוש | 6158 |
| חלקה | מספר חלקה | 23 |
| סוג מדידה | קטגוריה | מדידה לרישום, מדידה טופוגרפית, מדידה להיתר |
| מודד אחראי | שם המודד | "ישראל ישראלי, מודד מוסמך מס' 1234" |
| תאריך מדידה | תאריך ביצוע | 09/04/2026 |
| מערכת קואורדינטות | מערכת הייחוס | רשת ישראל החדשה (ITM) / WGS84 |
| סטטוס | שלב נוכחי | בתכנון / בביצוע / הושלם / הוגש |
| הערות | הערות חופשיות | "יש בעיית גישה מצד דרום" |

---

## 📤 פלט — תוצרים ודוחות

### תצוגת מפה אינטראקטיבית

| יכולת | תיאור |
|--------|--------|
| 🗺️ תצוגת מפה | מפה אינטראקטיבית עם שכבות מדידה |
| 🔍 חיפוש מרחבי | לחיצה/ציור אזור ← שליפת כל המדידות בתוך האזור |
| 📅 סינון לפי תאריכים | בחירת טווח תאריכים (מ-תאריך עד-תאריך) לסינון מדידות |
| 🏷️ סינון לפי סוג מדידה | סינון לפי קטגוריה: מדידה לרישום, טופוגרפית, להיתר, לפיצול וכו' |
| 🔎 סינון משולב | שילוב פילטרים: אזור + תאריכים + סוג מדידה + סטטוס + מודד |
| 📍 Clustering | קיבוץ נקודות מדידה בזום רחוק |
| 🎨 שכבות | הפעלה/כיבוי שכבות (גושים, חלקות, מדידות, תב"ע) |
| 📏 כלי מדידה | מדידת מרחקים ושטחים על המפה |
| 🔄 השוואה | השוואת מדידות שונות באותו אזור |

### דוחות ליצוא

| דוח | פורמט | תיאור |
|------|--------|--------|
| סיכום פרויקט | PDF | דוח מלא עם מפה, פרטי לקוח, קבצים, וציר זמן |
| רשימת מדידות באזור | PDF / Excel | כל המדידות בטווח גאוגרפי מסוים |
| מפת סטטוס | PNG / PDF | מפה צבעונית לפי סטטוס פרויקטים |
| דוח מודד | PDF | ריכוז עבודות לפי מודד ותקופה |
| ייצוא נתונים | GeoJSON / SHP / DXF / CSV / KMZ | ייצוא גאומטריות ונתונים מהמערכת |
| דוח לקוח | PDF | ריכוז פרויקטים ללקוח מסוים |
| תעודת מדידה | PDF | תעודת סיום מדידה (לפי תבנית) |

### התראות ועדכונים

| התראה | תיאור |
|--------|--------|
| 📧 מדידה חדשה באזור | התראה כשמועלית מדידה חדשה באזור שעבדת בו |
| ⏰ תזכורת דדליין | תזכורת על מועד הגשה קרב |
| ✅ שינוי סטטוס | עדכון כשפרויקט משנה סטטוס |
| 📱 Push Notification | התראות למכשיר נייד |

---

## 🗄️ בסיס נתונים

### טכנולוגיה

**PostgreSQL 16 + PostGIS 3.4** — בסיס נתונים רלציוני עם הרחבת GIS מלאה.

### דיאגרמת ER (Entity Relationship)

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   users      │     │   clients     │     │  survey_types   │
├─────────────┤     ├──────────────┤     ├────────────────┤
│ id (PK)      │     │ id (PK)       │     │ id (PK)         │
│ full_name    │     │ name          │     │ name            │
│ email        │     │ contact_name  │     │ description     │
│ phone        │     │ phone         │     └────────────────┘
│ role         │     │ email         │             │
│ license_num  │     │ address       │             │
│ is_active    │     │ notes         │             │
│ created_at   │     │ created_at    │             │
└──────┬──────┘     └──────┬───────┘             │
       │                    │                      │
       │ 1:N                │ 1:N                  │ 1:N
       ▼                    ▼                      ▼
┌──────────────────────────────────────────────────────────┐
│                       projects                            │
├──────────────────────────────────────────────────────────┤
│ id (PK)                                                   │
│ name                                                      │
│ description                                               │
│ client_id (FK → clients)                                  │
│ surveyor_id (FK → users)                                  │
│ manager_id (FK → users)                                   │
│ survey_type_id (FK → survey_types)                        │
│ status (enum: planned/in_progress/completed/submitted)    │
│ gush (מספר גוש)                                           │
│ helka (מספר חלקה)                                          │
│ address                                                   │
│ city                                                      │
│ area_sqm (שטח במ"ר)                                       │
│ coordinate_system (ITM/WGS84/ICS/other)                   │
│ survey_date                                               │
│ due_date                                                  │
│ notes                                                     │
│ bbox (geometry — Bounding Box של הפרויקט)                  │
│ center_point (geometry — נקודת מרכז)                       │
│ created_at                                                │
│ updated_at                                                │
└────────────┬──────────────────────────────┬──────────────┘
             │                              │
             │ 1:N                          │ 1:N
             ▼                              ▼
┌────────────────────┐          ┌──────────────────────────┐
│   survey_files      │          │   geo_features            │
├────────────────────┤          ├──────────────────────────┤
│ id (PK)             │          │ id (PK)                   │
│ project_id (FK)     │          │ project_id (FK)           │
│ original_filename   │          │ feature_type (point/      │
│ stored_path         │          │   line/polygon)           │
│ file_type           │          │ geometry (PostGIS)        │
│ file_size_bytes     │          │ layer_name                │
│ mime_type           │          │ properties (JSONB)        │
│ uploaded_by (FK)    │          │ source_file_id (FK →      │
│ description         │          │   survey_files)           │
│ uploaded_at         │          │ coordinate_system         │
│ is_primary          │          │ elevation                 │
└────────────────────┘          │ created_at                │
                                 └──────────────────────────┘

┌──────────────────────┐        ┌──────────────────────────┐
│   project_tags        │        │   activity_log            │
├──────────────────────┤        ├──────────────────────────┤
│ id (PK)               │        │ id (PK)                   │
│ project_id (FK)       │        │ user_id (FK)              │
│ tag_name              │        │ project_id (FK, nullable) │
│ created_at            │        │ action                    │
└──────────────────────┘        │ details (JSONB)           │
                                 │ ip_address                │
                                 │ created_at                │
                                 └──────────────────────────┘
```

### טבלאות עיקריות — פירוט

#### `users` — משתמשים
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    phone           VARCHAR(20),
    role            VARCHAR(20) CHECK (role IN ('admin', 'manager', 'surveyor')),
    license_number  VARCHAR(20),         -- מספר רישיון מודד
    avatar_url      VARCHAR(500),
    is_active       BOOLEAN DEFAULT true,
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### `clients` — לקוחות
```sql
CREATE TABLE clients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    contact_name    VARCHAR(100),
    phone           VARCHAR(20),
    email           VARCHAR(150),
    address         TEXT,
    id_number       VARCHAR(20),         -- ת.ז / ח.פ.
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### `projects` — פרויקטים
```sql
CREATE TABLE projects (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(300) NOT NULL,
    description       TEXT,
    client_id         UUID REFERENCES clients(id),
    surveyor_id       UUID REFERENCES users(id),
    manager_id        UUID REFERENCES users(id),
    survey_type_id    UUID REFERENCES survey_types(id),
    status            VARCHAR(20) DEFAULT 'planned'
                      CHECK (status IN ('planned','in_progress','completed','submitted','archived')),
    gush              VARCHAR(10),
    helka             VARCHAR(10),
    sub_helka         VARCHAR(10),
    address           TEXT,
    city              VARCHAR(100),
    area_sqm          NUMERIC(12,2),
    coordinate_system VARCHAR(20) DEFAULT 'ITM',
    survey_date       DATE,
    due_date          DATE,
    completion_date   DATE,
    notes             TEXT,
    bbox              GEOMETRY(Polygon, 2039),   -- ITM SRID
    center_point      GEOMETRY(Point, 2039),
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- אינדקס מרחבי לחיפוש גאוגרפי מהיר
CREATE INDEX idx_projects_bbox ON projects USING GIST (bbox);
CREATE INDEX idx_projects_center ON projects USING GIST (center_point);
CREATE INDEX idx_projects_status ON projects (status);
CREATE INDEX idx_projects_gush_helka ON projects (gush, helka);
```

#### `survey_files` — קבצי מדידה
```sql
CREATE TABLE survey_files (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        UUID REFERENCES projects(id) ON DELETE CASCADE,
    original_filename VARCHAR(500) NOT NULL,
    stored_path       VARCHAR(1000) NOT NULL,
    file_type         VARCHAR(20) NOT NULL,      -- dwg, dxf, shp, csv, geojson, las, pdf...
    file_size_bytes   BIGINT,
    mime_type         VARCHAR(100),
    uploaded_by       UUID REFERENCES users(id),
    description       TEXT,
    is_primary        BOOLEAN DEFAULT false,      -- קובץ המדידה העיקרי
    processing_status VARCHAR(20) DEFAULT 'pending'
                      CHECK (processing_status IN ('pending','processing','completed','failed')),
    processing_error  TEXT,
    metadata          JSONB,                      -- מטא-דאטה נוסף מהקובץ
    uploaded_at       TIMESTAMPTZ DEFAULT NOW()
);
```

#### `geo_features` — ישויות גאוגרפיות (המידע שחולץ מהקבצים)
```sql
CREATE TABLE geo_features (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_file_id    UUID REFERENCES survey_files(id) ON DELETE SET NULL,
    feature_type      VARCHAR(20) NOT NULL
                      CHECK (feature_type IN ('point','line','polygon','multipoint','multiline','multipolygon')),
    geometry          GEOMETRY(Geometry, 2039) NOT NULL,
    layer_name        VARCHAR(200),
    properties        JSONB DEFAULT '{}',
    elevation         NUMERIC(10,3),
    coordinate_system VARCHAR(20) DEFAULT 'ITM',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_geo_features_geom ON geo_features USING GIST (geometry);
CREATE INDEX idx_geo_features_project ON geo_features (project_id);
CREATE INDEX idx_geo_features_layer ON geo_features (layer_name);
```

#### `survey_types` — סוגי מדידה
```sql
CREATE TABLE survey_types (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color       VARCHAR(7) DEFAULT '#3388ff',  -- צבע תצוגה על המפה
    icon        VARCHAR(50)
);

-- נתוני ברירת מחדל
INSERT INTO survey_types (name, description, color) VALUES
    ('מדידה לרישום',        'מדידה לצורך רישום בטאבו',          '#2196F3'),
    ('מדידה טופוגרפית',     'מדידה טופוגרפית לתכנון',           '#4CAF50'),
    ('מדידה להיתר בנייה',   'מדידה לצורך הגשת היתר בנייה',     '#FF9800'),
    ('מדידה לפיצול/איחוד',  'מדידה לפיצול או איחוד חלקות',     '#9C27B0'),
    ('מדידה לתשתיות',       'מדידה לביצוע תשתיות',              '#F44336'),
    ('מדידה לצורכי תכנון',  'מדידה למטרות תכנון כלליות',       '#00BCD4'),
    ('בקרה הנדסית',         'בקרת מדידות ופיקוח',               '#795548'),
    ('סריקת לייזר',         'סריקת LiDAR וענני נקודות',         '#607D8B');
```

---

## 🗺️ מנוע מפות — Google Earth

> 🔒 **הערה:** הבחירה ב-Google Earth כמנוע המפות נובעת מדרישות **אבטחת מידע** (תשתית Google Workspace עם הצפנה והרשאות מתקדמות) ומהאינטגרציה הטבעית עם **יומן העבודות הקיים ב-Google Sheets**.

### שכבות מפה

| שכבה | מקור | תיאור |
|-------|-------|--------|
| מפת רקע — לווין | Google Earth | תצלום לווין / אוויר עדכני (שכבת ברירת מחדל) |
| מפת רקע — 3D Terrain | Google Earth | מודל תלת-ממדי של פני השטח |
| מפת רקע — רחובות | Google Maps / Earth | מפת רחובות ומבנים |
| גושים וחלקות | GovMap API (KML Overlay) | שכבת קדסטר רשמית |
| מדידות — נקודות | PostGIS → KML | נקודות מדידה מ-DB |
| מדידות — פוליגונים | PostGIS → KML | תחומי מדידה מ-DB |
| מדידות — קווים | PostGIS → KML | קווים (גבולות, חתכים) מ-DB |
| תב"ע | GovMap API (KML Overlay) | שכבת תב"ע |
| יומן עבודות | Google Sheets (סנכרון) | שכבת עבודות פעילות מתוך יומן העבודות |

### כלי מפה

- 🔍 **חיפוש מרחבי** — ציור מלבן/עיגול/פוליגון ← שליפת כל המדידות בתוך האזור
- 📍 **Geocoding** — חיפוש לפי כתובת, גוש/חלקה, או קואורדינטות
- 📏 **מדידת מרחק** — מדידת מרחק בין שתי נקודות (Google Earth Ruler)
- 📐 **מדידת שטח** — חישוב שטח פוליגון
- 🖨️ **הדפסת מפה** — ייצוא תצוגת המפה הנוכחית ל-PDF/PNG
- 🔄 **רפרוייקציה** — המרה בין מערכות קואורדינטות (ITM ↔ WGS84 ↔ ICS)
- 🌐 **תצוגת 3D** — ניצול יכולות התלת-ממד של Google Earth להצגת מדידות על פני השטח

### מערכות קואורדינטות

| מערכת | EPSG | שימוש |
|--------|------|--------|
| רשת ישראל החדשה (ITM) | 2039 | מערכת ברירת מחדל — מדידות ארציות |
| WGS84 | 4326 | GPS, מפות web |
| רשת ישראל הישנה (ICS) | 28193 (קירוב) | תאימות לאחור עם מדידות ישנות |

---

## 🔌 API — ממשק תכנות

### REST API Endpoints

#### פרויקטים
```
GET     /api/projects                    # רשימת כל הפרויקטים (עם פילטרים)
GET     /api/projects/:id                # פרויקט בודד
POST    /api/projects                    # יצירת פרויקט חדש
PUT     /api/projects/:id                # עדכון פרויקט
DELETE  /api/projects/:id                # מחיקת פרויקט
GET     /api/projects/:id/files          # קבצים של פרויקט
GET     /api/projects/:id/features       # ישויות גאוגרפיות של פרויקט
```

**פרמטרי סינון (Query Parameters) לרשימת פרויקטים:**
```
?date_from=2025-01-01&date_to=2026-04-09   # סינון לפי טווח תאריכים
?survey_type=מדידה+לרישום                   # סינון לפי סוג מדידה
?status=completed                           # סינון לפי סטטוס
?surveyor_id=UUID                           # סינון לפי מודד
?gush=6158&helka=23                        # סינון לפי גוש/חלקה
?city=רמת+גן                                # סינון לפי עיר
?sort_by=survey_date&order=desc            # מיון תוצאות
?page=1&limit=50                            # עימוד (Pagination)
```

#### חיפוש מרחבי
```
POST    /api/search/spatial              # חיפוש לפי גאומטריה (bbox/polygon)
GET     /api/search/address?q=...        # חיפוש לפי כתובת
GET     /api/search/parcel?gush=&helka=  # חיפוש לפי גוש וחלקה
GET     /api/search/radius?lat=&lng=&r=  # חיפוש ברדיוס
```

#### קבצים
```
POST    /api/files/upload                # העלאת קובץ מדידה
GET     /api/files/:id/download          # הורדת קובץ
DELETE  /api/files/:id                   # מחיקת קובץ
GET     /api/files/:id/preview           # תצוגה מקדימה (GeoJSON)
```

#### גאומטריות
```
GET     /api/features                    # כל הישויות (עם פילטר bbox)
GET     /api/features/:id                # ישות בודדת
POST    /api/features                    # יצירת ישות ידנית
GET     /api/features/export?format=     # ייצוא (geojson/shp/dxf/csv/kml)
```

#### משתמשים ולקוחות
```
POST    /api/auth/login                  # כניסה
POST    /api/auth/refresh                # רענון טוקן
GET     /api/users                       # רשימת משתמשים
GET     /api/clients                     # רשימת לקוחות
POST    /api/clients                     # יצירת לקוח
```

#### דוחות
```
GET     /api/reports/project/:id         # דוח פרויקט (PDF)
GET     /api/reports/area                # דוח אזורי (PDF)
GET     /api/reports/surveyor/:id        # דוח מודד (PDF)
GET     /api/reports/statistics          # סטטיסטיקות כלליות
```

### WebSocket Events
```
survey:file:uploaded     # קובץ הועלה
survey:file:processed    # קובץ עובד בהצלחה
survey:status:changed    # סטטוס פרויקט השתנה
survey:feature:added     # ישות גאוגרפית נוספה
```

---

## ⚙️ טכנולוגיות

### Frontend (לקוח)

| טכנולוגיה | תפקיד |
|-----------|--------|
| **React 18+** | ספריית UI |
| **TypeScript** | Type Safety |
| **Google Earth API** / **Google Maps JavaScript API** | מנוע מפות (ממשק Google Earth) |
| **Turf.js** | חישובים גאומטריים בצד הלקוח |
| **Proj4js** | המרת מערכות קואורדינטות |
| **React Query (TanStack)** | ניהול state של שרת |
| **Zustand** | ניהול state מקומי |
| **React Router** | ניתוב |
| **Recharts** | גרפים ותרשימים |
| **React-Dropzone** | העלאת קבצים (Drag & Drop) |
| **Vite** | Build tool |

### Backend (שרת)

| טכנולוגיה | תפקיד |
|-----------|--------|
| **Python 3.12+** | סביבת הרצה |
| **Flask 3.x** | HTTP framework |
| **SQLAlchemy + GeoAlchemy2** | ORM לבסיס נתונים (כולל תמיכת PostGIS) |
| **Alembic** | מיגרציות בסיס נתונים |
| **Marshmallow / Pydantic** | Validation וסריאליזציה |
| **ezdxf** | פרסור קבצי DXF |
| **ODA File Converter** / **libredwg** | המרת קבצי DWG ל-DXF לצורך פרסור |
| **Fiona + pyshp** | פרסור קבצי Shapefile |
| **Pandas** | פרסור קבצי CSV ועיבוד נתונים |
| **Pillow** | עיבוד תמונות |
| **ReportLab / WeasyPrint** | יצירת דוחות PDF |
| **Flask-SocketIO** | WebSocket לעדכונים בזמן אמת |
| **gspread + googleapis** | סנכרון עם יומן עבודות ב-Google Sheets |
| **Google Earth Engine API** | עיבוד נתונים גאו-מרחביים |
| **Celery** | תורי עבודה לעיבוד קבצים |
| **Loguru** | לוגים |
| **Shapely + pyproj** | חישובים גאומטריים והמרת קואורדינטות |
| **GeoPandas** | עיבוד נתונים גאו-מרחביים |

### בסיס נתונים ותשתית

| טכנולוגיה | תפקיד |
|-----------|--------|
| **PostgreSQL 16** | בסיס נתונים רלציוני |
| **PostGIS 3.4** | הרחבת GIS ל-PostgreSQL |
| **Redis** | Cache + תורי עבודה |
| **MinIO** (או S3) | אחסון קבצים |
| **Google Workspace** | אבטחת מידע, Google Sheets, Google Earth, Drive |
| **Docker** | קונטיינריזציה |
| **Nginx** | Reverse Proxy |

---

## 🚀 התקנה והרצה

### דרישות מקדימות

- **Python** >= 3.12
- **PostgreSQL** >= 16 עם **PostGIS** >= 3.4
- **Redis** >= 7
- **Docker** + **Docker Compose** (מומלץ)

### הרצה עם Docker (מומלץ)

```bash
# שכפול הפרויקט
git clone https://github.com/your-org/survey-gis.git
cd survey-gis

# העתקת קובץ סביבה
cp .env.example .env
# עריכת .env עם הערכים הנדרשים

# הרצה
docker compose up -d

# המערכת תהיה זמינה ב:
# Frontend:  http://localhost:3000
# Backend:   http://localhost:5000
# DB Admin:  http://localhost:5050 (pgAdmin)
```

### הרצה מקומית (Development)

```bash
# יצירת סביבה וירטואלית והתקנת תלויות (שרת)
cd server
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# התקנת תלויות לקוח
cd ../client && npm install

# הגדרת בסיס נתונים
cd ../server
alembic upgrade head       # הרצת מיגרציות
python seed.py             # נתוני דוגמה

# הרצת שרת
python app.py              # http://localhost:5000

# הרצת Celery Worker (בטרמינל נפרד)
celery -A app.celery worker --loglevel=info

# הרצת לקוח (בטרמינל נפרד)
cd ../client
npm run dev               # http://localhost:3000
```

### משתני סביבה (`.env`)

```env
# Database
DATABASE_URL=postgresql://survey:password@localhost:5432/survey_gis?schema=public

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-super-secret-key
JWT_EXPIRES_IN=7d

# File Storage
STORAGE_TYPE=local           # local | s3 | minio
STORAGE_PATH=./uploads
# MINIO_ENDPOINT=localhost
# MINIO_PORT=9000
# MINIO_ACCESS_KEY=minioadmin
# MINIO_SECRET_KEY=minioadmin

# Google Services
GOOGLE_EARTH_API_KEY=your-google-earth-api-key
GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id
GOOGLE_SERVICE_ACCOUNT_KEY=./config/google-service-account.json

# Map Services
GOVMAP_API_KEY=your-govmap-api-key

# Server
PORT=5000
FLASK_ENV=development
FLASK_DEBUG=1
```

---

## 🔄 תהליכי עבודה

### תהליך 1: העלאת מדידה חדשה

```
מנהל פרויקט / אדמין מעלה מפה סופית (DWG/DXF/SHP/CSV...)
         │
         ▼
  ┌──────────────┐
  │  Validation   │  בדיקת תקינות קובץ
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  File Storage │  שמירת הקובץ המקורי
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Processing   │  חילוץ גאומטריות ← תור עבודה (Celery)
  │  Queue        │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Geo Parser   │  פרסור הקובץ:
  │               │  - DWG → המרה ל-DXF → חילוץ שכבות ואלמנטים
  │               │  - DXF → חילוץ שכבות ואלמנטים
  │               │  - SHP → קריאת geometries + attributes
  │               │  - CSV → יצירת נקודות מ-X,Y,Z
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Reprojection │  המרה ל-ITM (EPSG:2039) אם צריך
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  DB Insert    │  הכנסה ל-geo_features + עדכון bbox
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Notification │  WebSocket → עדכון המפה בזמן אמת
  └──────────────┘
```

### תהליך 2: חיפוש מרחבי

```
המשתמש מצייר אזור על המפה / מחפש כתובת
         │
         ▼
  ┌──────────────────┐
  │  Geocode / BBox   │  המרה לגאומטריה
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │  PostGIS Query    │  ST_Intersects / ST_Within
  │                   │  חיפוש בטבלת projects + geo_features
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │  Results          │  תוצאות עם:
  │                   │  - רשימת פרויקטים
  │                   │  - KML להצגה על Google Earth
  │                   │  - פרטי לקוח ומודד
  └──────────────────┘
```

### תהליך 3: עבודה מהשטח (מודד — צפייה בלבד)

```
                 ┌──────────────┐
                 │  פתיחת PWA    │  אפליקציה ניידת
                 │  בטלפון      │
                 └──────┬───────┘
                        │
      ┌─────────────┬───┴────────────┬──────────────┐
      ▼             ▼                ▼              ▼
┌──────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ צפייה    │ │ סינון לפי  │ │ ניווט      │ │ הורדת      │
│ במפה +   │ │ תאריכים /  │ │ לנקודה     │ │ קבצים      │
│ מדידות   │ │ סוג מדידה  │ │            │ │ רלוונטיים  │
│ קיימות   │ │            │ │            │ │            │
└──────────┘ └────────────┘ └────────────┘ └────────────┘

⚠️ מודדים אינם מעלים קבצים — רק מנהלי פרויקט מעלים מפות סופיות
```

---

## 🔒 אבטחה והרשאות

### אימות (Authentication)

- **JWT** — טוקן מבוסס JSON Web Token
- **Google Workspace** — אימות דרך חשבון Google ארגוני
- **Refresh Token** — טוקן ארוך טווח לרענון
- **bcrypt** — הצפנת סיסמאות

### הרשאות (Authorization) — RBAC

| פעולה | Admin | Manager | Surveyor |
|-------|:-----:|:-------:|:--------:|
| ניהול משתמשים | ✅ | ❌ | ❌ |
| יצירת פרויקט | ✅ | ✅ | ❌ |
| עריכת כל הפרויקטים | ✅ | ✅ | ❌ |
| עריכת פרויקטים משלו | ✅ | ✅ | ✅ |
| העלאת קבצים (מפות סופיות) | ✅ | ✅ | ❌ |
| סינון לפי תאריכים | ✅ | ✅ | ✅ |
| סינון לפי סוג מדידה | ✅ | ✅ | ✅ |
| מחיקת קבצים | ✅ | ✅ | ❌ |
| צפייה במפה | ✅ | ✅ | ✅ |
| חיפוש מרחבי | ✅ | ✅ | ✅ |
| הפקת דוחות | ✅ | ✅ | ❌ |
| הגדרות מערכת | ✅ | ❌ | ❌ |
| צפייה בלוגים | ✅ | ❌ | ❌ |

---

## 🗓️ Roadmap — תכנית פיתוח

### שלב 1 — MVP (חודשים 1-2) 🎯

- [x] תכנון ארכיטקטורה ו-DB
- [ ] הקמת שרת Flask + SQLAlchemy
- [ ] הקמת בסיס נתונים PostgreSQL + PostGIS
- [ ] מערכת אימות (Login / JWT + Google Workspace)
- [ ] CRUD פרויקטים ולקוחות
- [ ] העלאת קבצים בסיסית (DWG, DXF, CSV)
- [ ] סינון לפי טווח תאריכים וסוג מדידה
- [ ] מפה אינטראקטיבית עם Google Earth API
- [ ] הצגת פרויקטים על המפה (KML layers)
- [ ] חיפוש מרחבי בסיסי (BBox)
- [ ] אינטגרציה בסיסית עם Google Sheets (יומן עבודות — קריאה)

### שלב 2 — גרסה מלאה (חודשים 3-4) 🚀

- [ ] פרסור אוטומטי DXF (שכבות + גאומטריות)
- [ ] תמיכה ב-Shapefile, GeoJSON, KML
- [ ] סנכרון דו-כיווני עם Google Sheets (יומן עבודות — קריאה וכתיבה)
- [ ] חיפוש לפי גוש/חלקה
- [ ] חיפוש לפי כתובת (Geocoding — Google Maps)
- [ ] מערכת דוחות PDF
- [ ] שכבת גושים וחלקות (GovMap → KML Overlay)
- [ ] PWA — גרסה ניידת
- [ ] תור עבודה לעיבוד קבצים (Celery)
- [ ] התראות WebSocket

### שלב 3 — התקדמות (חודשים 5-6) ⚡

- [ ] תמיכה בענני נקודות (LAS/LAZ)
- [ ] השוואת מדידות (overlay ב-Google Earth)
- [ ] דוחות מתקדמים + סטטיסטיקות
- [ ] אינטגרציה עם GovMap API
- [ ] ייצוא ל-DXF / SHP / KMZ
- [ ] ניהול גרסאות קבצים
- [ ] חיפוש טקסט מלא (Full-Text Search)
- [ ] שיתוף פרויקטים דרך Google Earth קישורי KML

### שלב 4 — אופטימיזציה (חודשים 7+) 🔧

- [ ] תמיכה בתמונות אורתופוטו (Raster tiles)
- [ ] ניתוח AI — זיהוי אוטומטי של גבולות חלקות
- [ ] אינטגרציה עם מערכת הנהלת חשבונות
- [ ] API פתוח לאינטגרציה עם תוכנות מדידה
- [ ] אפליקציה native (React Native)
- [ ] Offline mode למודדים בשטח
- [ ] Google Earth Engine — ניתוחים מרחביים מתקדמים

---

## 📁 מבנה תיקיות הפרויקט

```
survey-gis/
├── client/                    # Frontend (React)
│   ├── public/
│   ├── src/
│   │   ├── assets/            # תמונות, אייקונים
│   │   ├── components/        # רכיבי UI
│   │   │   ├── common/        # כפתורים, טפסים, מודלים
│   │   │   ├── map/           # רכיבי מפה (Google Earth)
│   │   │   ├── projects/      # רכיבי פרויקטים
│   │   │   └── layout/        # Header, Sidebar, Footer
│   │   ├── hooks/             # Custom React Hooks
│   │   ├── pages/             # דפי האפליקציה
│   │   ├── services/          # קריאות API + Google Sheets
│   │   ├── store/             # State Management (Zustand)
│   │   ├── types/             # TypeScript Types
│   │   ├── utils/             # פונקציות עזר
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── server/                    # Backend (Python / Flask)
│   ├── app.py                 # נקודת כניסה ראשית
│   ├── config.py              # הגדרות (כולל Google Service Account)
│   ├── requirements.txt       # תלויות Python
│   ├── models/                # מודלים (SQLAlchemy + GeoAlchemy2)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── client.py
│   │   ├── project.py
│   │   ├── survey_file.py
│   │   └── geo_feature.py
│   ├── routes/                # ניתובים (Blueprints)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── clients.py
│   │   ├── files.py
│   │   ├── features.py
│   │   ├── search.py
│   │   └── reports.py
│   ├── services/              # לוגיקה עסקית
│   │   ├── geo/               # שירותי GIS (parser, reproject)
│   │   ├── files/             # ניהול קבצים
│   │   ├── google/            # שירותי Google (Sheets, Earth)
│   │   ├── reports/           # הפקת דוחות
│   │   └── search/            # חיפוש מרחבי
│   ├── middleware/            # Middleware (auth, validation)
│   ├── tasks/                 # תורי עבודה (Celery)
│   │   ├── __init__.py
│   │   └── file_processing.py
│   ├── schemas/               # Marshmallow / Pydantic schemas
│   ├── utils/                 # פונקציות עזר
│   ├── alembic/               # מיגרציות בסיס נתונים
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── seed.py                # נתוני דוגמה
│   └── uploads/               # אחסון קבצים מקומי
│
├── docker/
│   ├── Dockerfile.client
│   ├── Dockerfile.server
│   └── nginx.conf
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---


---

<div align="center">
<sub>נבנה עם ❤️ עבור משרד המדידות — 2026</sub>
</div>

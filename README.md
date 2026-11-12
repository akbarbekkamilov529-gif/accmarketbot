# TG Account Marketplace Bot

Telegram uchun to'liq avtomatlashtirilgan account marketplace boti. **Admin panel, admin menyu va admin ID yo'q** — barcha jarayonlar avtomatik ishlaydi.

## Imkoniyatlar

- Doimiy reply menyu: profil, balans, sotib olish, sotish, buyurtmalar, e'lonlar, tarix, statistika va sozlamalar.
- `/start` profil sahifasini ochadi: ism, username, Telegram ID, balans, savdo statistikasi, reyting va ro'yxatdan o'tgan sana.
- Uch tilli interfeys: o'zbek, rus va ingliz; tanlangan til bazada saqlanadi.
- Seller akkaunt qo'shadi: platforma, nickname, skrinshotlar, tavsif, login/parol, qo'shimcha maydonlar, narx.
- E'lon yaratishdan oldin preview, tahrirlash va ogohlantirish ekrani.
- Buyer platforma bo'yicha qidirish, filtrlash, sahifalash, akkaunt kartasi va batafsil ko'rinish.
- Escrow: to'lovdan keyin seller ulushi `pending`ga o'tadi, buyer tasdiqlagach qolgan qismi `available` bo'ladi.
- Har soatda seller ulushining 5% qismi avtomatik chiqariladi (maksimum 20 soat).
- Buyer akkaunt ma'lumotlarini faqat to'lovdan keyin ko'radi.
- Nizo: buyer/seller xabarlari, dalillar, escrow muzlatish, avtomatik refund yo'q.
- Reyting va izohlar, bildirishnomalar, balance va tranzaksiyalar tarixi.
- Login/parol AES-GCM bilan shifrlanadi. Parol xabarlari chatdan o'chiriladi.

## Texnologiyalar

- Python 3.11+ (Render uchun 3.12 tavsiya etiladi)
- aiogram 3.31
- SQLAlchemy 2 async + asyncpg
- PostgreSQL + Alembic
- Pydantic Settings
- APScheduler
- cryptography (AES-GCM)

## Struktura

```text
app/
  bot.py, config.py, constants.py, crypto.py, database.py
  handlers/     # common, profile, seller, buyer, orders, disputes, reviews
  keyboards/    # reply va inline klaviaturalar
  middlewares/  # database, user, rate limit
  models/       # SQLAlchemy modellari
  services/     # account, order, escrow, release, payment, dispute, review
  states/       # FSM holatlari
migrations/     # Alembic env va versiyalar
tests/          # pytest testlari
main.py         # polling yoki webhook entrypoint
render.yaml     # Render blueprint
Dockerfile
```

## Lokal ishga tushirish (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

`.env` faylini to'ldiring. `.env.example` ichida real token ataylab yozilmagan — `BOT_TOKEN` qatorini qo'lda qo'shing:

```dotenv
BOT_TOKEN=123456:telegram-bot-token
CREDENTIAL_ENCRYPTION_KEY=...
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace
ENVIRONMENT=development
USE_WEBHOOK=false
```

Lokal polling ishga tushganda HTTP server ham `http://127.0.0.1:8080/health`da ochiladi. Agar Telegram'da webhook allaqachon o'rnatilgan bo'lsa (masalan Render servisi ishlayotgan bo'lsa), lokal polling o'zini to'xtatadi va webhook'ni o'chirmaydi. Ataylab almashtirmoqchi bo'lsangizgina `POLLING_FORCE=true` qiling.

Shifrlash kalitini yarating:

```powershell
python -c "from app.crypto import generate_key; print(generate_key())"
```

PostgreSQL bazasini yarating:

```sql
CREATE DATABASE marketplace;
```

Migratsiyalarni qo'llang va botni ishga tushiring:

```powershell
python -m alembic upgrade head
python main.py
```

`AUTO_CREATE_TABLES=false` bo'lsa, jadvallar faqat Alembic orqali yaratiladi. Ishlab chiqishda vaqtincha `true` qilish mumkin, productionda `false` qoldiring.

## Testlar

```powershell
python -m pytest
```

Testlar SQLite in-memory bazada ishlaydi, lokal PostgreSQL talab qilmaydi.

## Muhim env o'zgaruvchilari

| O'zgaruvchi | Tavsif |
| --- | --- |
| `BOT_TOKEN` | Telegram bot tokeni (majburiy) |
| `CREDENTIAL_ENCRYPTION_KEY` | AES-GCM kaliti (majburiy, productionda) |
| `DATABASE_URL` | PostgreSQL URL; `postgresql://` avtomatik asyncpg'ga o'giriladi |
| `ENVIRONMENT` | `development`, `production`, `test` |
| `USE_WEBHOOK` | `true` bo'lsa webhook, `false` bo'lsa polling. Render'da avtomatik `true` |
| `WEBHOOK_BASE_URL` | Webhook uchun tashqi URL; Render'da `RENDER_EXTERNAL_URL` avtomatik ishlatiladi |
| `WEBHOOK_SECRET` | Telegram webhook secret token; faqat `A-Z a-z 0-9 _ -` belgilari |
| `HOST` / `PORT` | HTTP server manzili; Render'da `PORT` avtomatik beriladi |
| `POLLING_FORCE` | Lokal polling mavjud webhook'ni almashtirishiga ruxsat beradi; odatda `false` |
| `PLATFORM_COMMISSION_RATE` | Platforma komissiyasi, default `7` (%) |
| `HOURLY_RELEASE_RATE` | Soatlik chiqarish ulushi, default `5` (%) |
| `PAYMENTS_ENABLED` | Haqiqiy to'lovlar yoqilganini bildiradi, default `false` |
| `PAYMENT_PROVIDER` | `skip`, `click` yoki `payme` |
| `SKIP_PAYMENT_ENABLED` | Demo SKIP PAYMENT tugmasini ko'rsatish |

To'liq ro'yxat `.env.example` faylida.

## Render deploy

1. Reponi GitHub'ga push qiling.
2. Render'da **New → Blueprint** tanlab, `render.yaml` faylini ulang.
3. `BOT_TOKEN`, `CREDENTIAL_ENCRYPTION_KEY`, `BOT_USERNAME`, `SUPPORT_CONTACT` qiymatlarini kiriting.
4. Deploy tugagach, servis URL'i `https://<service>.onrender.com` bo'ladi. `RENDER_EXTERNAL_URL` orqali webhook avtomatik sozlanadi.
5. Health check: `/health`.

Render muhitida bot **har doim webhook rejimida** ishlaydi (`RENDER` / `RENDER_EXTERNAL_URL` avtomatik aniqlanadi). HTTP server `0.0.0.0:${PORT}` manzilida ochiladi, shuning uchun `No open ports detected` xatosi chiqmaydi. Polling va webhook bir vaqtda ishlamaydi: webhook o'rnatilganda Telegram eski `getUpdates` sessiyasini avtomatik to'xtatadi.

Render start command `python -m alembic upgrade head && python main.py` bo'lgani uchun migratsiyalar har deployda qo'llanadi. **Bitta instance** ishlatilsin: scheduler va hourly release takrorlanmasligi kerak. Lokal kompyuterda ham xuddi shu `BOT_TOKEN` bilan polling ishga tushirmang — `TelegramConflictError: terminated by other getUpdates request` shu sababdan chiqadi.

Majburiy Render Environment Variables:

| O'zgaruvchi | Qiymat |
| --- | --- |
| `BOT_TOKEN` | BotFather'dan olingan token |
| `CREDENTIAL_ENCRYPTION_KEY` | 32-byte base64 kalit |
| `DATABASE_URL` | Render PostgreSQL `connectionString` |
| `ENVIRONMENT` | `production` |
| `USE_WEBHOOK` | `true` |
| `WEBHOOK_SECRET` | Render `generateValue` yoki o'zingizning xavfsiz token |
| `AUTO_CREATE_TABLES` | `false` |

`PORT` va `RENDER_EXTERNAL_URL` Render tomonidan avtomatik beriladi; qo'lda kiritish shart emas.

> Free plan'dagi web service vaqti-vaqti bilan uxlab qoladi, free PostgreSQL esa muddatli bo'ladi. Haqiqiy savdo uchun paid plan va muntazam backup tavsiya etiladi.

### Docker

```powershell
docker build -t tg-marketplace-bot .
docker run --env-file .env -e PORT=8080 -p 8080:8080 tg-marketplace-bot
```

Docker Render'da `PORT` avtomatik beriladi. Konteyner `alembic upgrade head`dan keyin `python main.py` ishga tushiradi va `0.0.0.0:${PORT}`da tinglaydi.

## Biznes qoidalari

- Narx `Decimal` va `Numeric(14,2)` bilan hisoblanadi, float ishlatilmaydi.
- Order yaratilganda akkaunt atomik `RESERVED` bo'ladi; partial unique index bir akkauntni ikki marta sotishni bloklaydi.
- Komissiya: `order.amount * PLATFORM_COMMISSION_RATE / 100`.
- Seller ulushi: `order.amount - commission`.
- Komissiya yakuniy summasi faqat muvaffaqiyatli to'lovdan keyin hisoblanadi va bitta tranzaksiya sifatida yoziladi; `orders.amount`, `orders.commission_amount`, `orders.seller_amount` alohida saqlanadi.
- Hourly release: seller ulushining `HOURLY_RELEASE_RATE` foizi, `HOURLY_RELEASE_INTERVAL_SECONDS` oralig'ida. `(order_id, hour_number)` unique bo'lgani uchun idempotent.
- Nizo ochilganda hourly release to'xtaydi. Nizoni avtomatik hal qilish yoki refund qilish yo'q — kelishuv yoki qo'lda aralashuv talab qilinadi.
- Buyer tasdiqlaganda qolgan escrow qismi sellerga chiqariladi.
- SKIP PAYMENT — demo: buyurtma yaratilmaydi, to'lov olinmaydi, sellerga pul yozilmaydi.

## To'lov provayderlari

`app/services/payment_service.py` ichida Click va Payme uchun interfeys tayyor, lekin real API chaqiruvlari ataylab yozilmagan. `PAYMENTS_ENABLED=true` qilishdan oldin:

1. Provayderning create payment / callback / payout API'larini implement qiling.
2. Webhook endpointlarini qo'shing va imzoni tekshiring.
3. `mark_succeeded` / `mark_failed` faqat imzosi tasdiqlangan callback'dan chaqirilishini ta'minlang.
4. Idempotency va replay attack himoyasini qo'shing.

## Xavfsizlik

- `.env` hech qachon repoga commit qilinmasin.
- Agar `BOT_TOKEN` biror fayl yoki git tarixiga tushib qolgan bo'lsa, BotFather'da `/revoke` qilib tokenni yangilang va Render + lokal `.env`dagi qiymatni almashtiring.
- `CREDENTIAL_ENCRYPTION_KEY`ni almashtirsangiz, mavjud shifrlangan ma'lumotlar o'qilmaydi. Kalitni xavfsiz saqlang va backup qiling.
- Bot tokeni va webhook secretni faqat Render Environment Variables'da saqlang.
- Ishlab chiqarishda PostgreSQL backup va monitoring yoqilsin.
- Bir nechta instance ishlatilsa, scheduler uchun alohida worker yoki distributed lock kerak.

```
app/
    akashic-venv/                 # virtualenv lokal (tidak di-commit)
    backend/
        database/
            __init__.py
            connection.py         # connection pool MySQL + helper transaksi
            db_akashic.sql        # skema + data awal
        models/
            __init__.py
            admin_model.py
            category_model.py
            event_model.py
            information_model.py
            news_model.py
            notification_model.py
            push_subscription_model.py
            region_model.py
        routes/
            __init__.py           # registrasi blueprint
            admin_routes.py       # dashboard, activity log, settings, kategori
            auth_routes.py        # login, logout, register, reset password, profil
            event_routes.py
            information_routes.py
            location_routes.py    # /api/location/detect, /api/feed
            news_routes.py        # berita, moderasi, sumber RSS, collect
            notification_routes.py
            page_routes.py        # render halaman HTML
            region_routes.py
        services/
            feed_engine.py        # gabungan information + event + news
            location_engine.py    # validasi koordinat sementara
            news_collector.py     # RSS + scheduler
            notification_engine.py# Web Push
            region_engine.py      # Polygon/MultiPolygon (Shapely)
        utils/
            api.py                # amplop respons JSON + APIError
            mailer.py             # SMTP opsional
            security.py           # sesi admin, CSRF, rate limit login
            validators.py
        app.py                    # application factory + entrypoint
        config.py                 # konfigurasi dari .env
        manage.py                 # CLI: create-admin, generate-vapid, collect-news
        requirements.txt
    catatan/
        database.md
        description.md
        struktur.md
    frontend/
        assets/
            css/
                style.css         # design system bersama
            img/
                icon.svg
            js/
                admin.js          # helper dasbor admin (tabel, form, dialog)
                api.js            # fetch wrapper, util DOM, toast
                feed.js           # render feed + detail
                location.js       # Geolocation API → /api/location/detect
                push.js           # Web Push subscription
            service_worker.js     # dilayani di /service_worker.js
        pages/
            admin/
                base-admin.html
                dashboard-admin.html
                events.html
                information.html
                news.html
                profile.html
                regions.html
                setting.html
            auth/
                base-auth.html
                forgot-password.html
                login.html
                register.html
                reset-password.html
            error/
                400.html
                500.html
            landing/
                about.html
                base.html
                index.html
                information.html
            legal/
                contact.html
                disclaimer.html
                system-description.html
    .env                          # konfigurasi lokal (tidak di-commit)
    .env.example
    .gitignore
    README.md
```

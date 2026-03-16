# canli.yigitgulyurt.net.tr Kurulum

## 1. Redis paketi yükle
```bash
sudo -u yigitgulyurt /var/www/yigitgulyurt/venv/bin/pip install redis==5.0.1
```

## 2. hls.js dosyasını kopyala
```bash
sudo cp /var/www/cagrivakti/app/static/js/hls.js \
        /var/www/yigitgulyurt/app/static/js/hls.js
sudo chown yigitgulyurt:www-data /var/www/yigitgulyurt/app/static/js/hls.js
```

## 3. .env dosyasına ekle
```
STREAM_KEY=cagrivakti'deki ile aynı key
REDIS_URL=redis://localhost:6379/0
```

## 4. Nginx config
```bash
sudo cp nginx_canli.conf /etc/nginx/sites-available/canli-yigitgulyurt
sudo ln -sf /etc/nginx/sites-available/canli-yigitgulyurt \
            /etc/nginx/sites-enabled/canli-yigitgulyurt
sudo nginx -t && sudo systemctl reload nginx
```

## 5. SSL
```bash
sudo certbot --nginx -d canli.yigitgulyurt.net.tr
```

## 6. Servisi yeniden başlat
```bash
sudo systemctl restart yigitgulyurt
```

## Erişim
https://canli.yigitgulyurt.net.tr/stream/STREAM_KEY

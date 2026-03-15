#!/bin/bash
# İlk kurulum scripti — sunucuda bir kez çalıştırılır

set -e

DEPLOY_DIR="/var/www/yigitgulyurt"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== yigitgulyurt.net.tr kurulum başlıyor ==="

# 1. Dosyaları kopyala
sudo mkdir -p $DEPLOY_DIR
sudo rsync -a --exclude='.git' $REPO_DIR/ $DEPLOY_DIR/
sudo chown -R yigitgulyurt:www-data $DEPLOY_DIR

# 2. Venv oluştur
sudo -u yigitgulyurt python3 -m venv $DEPLOY_DIR/venv
sudo -u yigitgulyurt $DEPLOY_DIR/venv/bin/pip install -r $DEPLOY_DIR/requirements.txt

# 3. DB migrate
cd $DEPLOY_DIR
sudo -u yigitgulyurt $DEPLOY_DIR/venv/bin/flask db init
sudo -u yigitgulyurt $DEPLOY_DIR/venv/bin/flask db migrate -m "initial"
sudo -u yigitgulyurt $DEPLOY_DIR/venv/bin/flask db upgrade

# 4. Admin kullanıcısı oluştur
sudo -u yigitgulyurt $DEPLOY_DIR/venv/bin/python << 'PYEOF'
from app import create_app, db
from app.models import Admin
app = create_app()
with app.app_context():
    if not Admin.query.first():
        a = Admin(username='admin')
        a.set_password('degistir-bunu!')
        db.session.add(a)
        db.session.commit()
        print("Admin oluşturuldu: admin / degistir-bunu!")
PYEOF

# 5. Nginx
sudo cp $REPO_DIR/nginx_yigitgulyurt.conf /etc/nginx/sites-available/yigitgulyurt
sudo ln -sf /etc/nginx/sites-available/yigitgulyurt /etc/nginx/sites-enabled/yigitgulyurt
sudo nginx -t && sudo systemctl reload nginx

# 6. Systemd
sudo cp $REPO_DIR/yigitgulyurt.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable yigitgulyurt
sudo systemctl start yigitgulyurt

echo ""
echo "=== Kurulum tamamlandı! ==="
echo "SSL için: sudo certbot --nginx -d yigitgulyurt.net.tr -d www.yigitgulyurt.net.tr"
echo "Durum:    sudo systemctl status yigitgulyurt"

#!/bin/bash
# Sunucuda çalıştır: sudo bash migrate_add_content.sh
cd /var/www/yigitgulyurt
source venv/bin/activate
flask db migrate -m "add project content field"
flask db upgrade
echo "Migration tamamlandı"

#!/bin/bash
cd /var/www/yigitgulyurt
source venv/bin/activate
flask db migrate -m "add stream_config table"
flask db upgrade
echo "Migration tamamlandı"

import os
import requests as req_lib
from flask import Blueprint, render_template, jsonify, request, abort, current_app

bp = Blueprint('stream', __name__, subdomain='canli')

try:
    import redis as redis_lib
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

_VIEWER_TIMEOUT = 45
_VIEWER_KEY_PREFIX = 'yg_viewer:'

def _get_redis():
    url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return redis_lib.from_url(url, decode_responses=True)

@bp.route('/<key>')
def canli(key):
    expected = current_app.config.get('STREAM_KEY', '')
    if not expected or key != expected:
        abort(404)
    stream_url = f'/canli-kaynak/canli/{key}/index.m3u8'
    return render_template('stream/canli.html', stream_url=stream_url)

@bp.route('/ping', methods=['POST'])
def stream_ping():
    data = request.get_json(silent=True) or {}
    sid = data.get('sid', '')
    if not sid:
        return jsonify({'ok': False}), 400
    if _REDIS_AVAILABLE:
        try:
            r = _get_redis()
            r.setex(f'{_VIEWER_KEY_PREFIX}{sid}', _VIEWER_TIMEOUT, '1')
        except Exception as e:
            current_app.logger.warning(f'Redis ping error: {e}')
    return jsonify({'ok': True})

@bp.route('/status')
def stream_status():
    key = current_app.config.get('STREAM_KEY', '')
    path_name = f'canli/{key}'
    try:
        r = req_lib.get('http://localhost:9997/v3/paths/list', timeout=2)
        items = r.json().get('items', [])
        path = next((p for p in items if p.get('name') == path_name), None)
        live = bool(path and path.get('ready'))
        return jsonify({'live': live})
    except Exception:
        fallback = current_app.config.get('STREAM_LIVE_FALLBACK', 'false').lower() == 'true'
        return jsonify({'live': fallback})

@bp.route('/viewers')
def stream_viewers():
    if not _REDIS_AVAILABLE:
        return jsonify({'viewers': 0})
    try:
        r = _get_redis()
        keys = r.keys(f'{_VIEWER_KEY_PREFIX}*')
        return jsonify({'viewers': len(keys)})
    except Exception as e:
        current_app.logger.warning(f'Redis viewers error: {e}')
        return jsonify({'viewers': 0})

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, render_template, jsonify, send_file, session, redirect, url_for
from functools import wraps
from collections import Counter
import os
import json
import time
import re
from werkzeug.security import generate_password_hash, check_password_hash
from utils.exif_extractor import extract_exif
from utils.baidu_map import reverse_geocode, get_nearby_attractions
from utils.vision_model import analyze_image
from utils.text_model import generate_travel_journal
from utils.exporter import journal_image_bytes, journal_pdf_bytes
from utils.database import (
    init_db, create_user, get_user_by_username, get_user_by_id,
    list_journals, get_journal, create_journal, update_journal_row,
    delete_journal_row, import_legacy_journals,
)

# 省份列表
PROVINCES = ['北京', '上海', '广东', '浙江', '江苏', '山东', '河北', '河南', '湖北', '湖南',
             '四川', '云南', '辽宁', '吉林', '黑龙江', '安徽', '福建', '江西', '山西', '陕西',
             '甘肃', '青海', '内蒙古', '广西', '贵州', '宁夏', '新疆', '西藏', '台湾', '香港', '澳门',
             '天津', '重庆', '海南']

# 城市到省份的映射
CITY_TO_PROVINCE = {
    '北京': '北京', '上海': '上海', '天津': '天津', '重庆': '重庆',
    '西安': '陕西', '延安': '陕西', '咸阳': '陕西',
    '广州': '广东', '深圳': '广东', '珠海': '广东', '佛山': '广东',
    '杭州': '浙江', '宁波': '浙江', '温州': '浙江',
    '南京': '江苏', '苏州': '江苏', '无锡': '江苏',
    '济南': '山东', '青岛': '山东', '烟台': '山东',
    '石家庄': '河北', '唐山': '河北',
    '郑州': '河南', '洛阳': '河南',
    '武汉': '湖北', '宜昌': '湖北',
    '长沙': '湖南', '岳阳': '湖南',
    '成都': '四川', '绵阳': '四川',
    '昆明': '云南', '大理': '云南', '丽江': '云南',
    '沈阳': '辽宁', '大连': '辽宁',
    '长春': '吉林',
    '哈尔滨': '黑龙江',
    '合肥': '安徽',
    '福州': '福建', '厦门': '福建',
    '南昌': '江西',
    '太原': '山西',
    '兰州': '甘肃',
    '西宁': '青海',
    '呼和浩特': '内蒙古',
    '南宁': '广西',
    '贵阳': '贵州',
    '银川': '宁夏',
    '乌鲁木齐': '新疆',
    '拉萨': '西藏',
    '台北': '台湾',
    '香港': '香港',
    '澳门': '澳门',
    '海口': '海南', '三亚': '海南'
}


def extract_province_city(text):
    """从文本中提取省份和城市，返回 (province, city)"""
    if not text:
        return None, None
    # 先匹配城市（更具体），再匹配省份
    for city, province in CITY_TO_PROVINCE.items():
        if city in text:
            return province, city
    for province in PROVINCES:
        if province in text:
            return province, None
    return None, None


def format_location(province, city):
    """格式化地点为 '省·市' 或 '省'"""
    if city and province and city != province:
        return f"{province}·{city}"
    if city:
        return city
    if province:
        return province
    return '未知地点'


# 天气关键词（按优先级排列，多云需先于晴/阴匹配；风类关键词需精确匹配短语，
# 避免将“建筑风格/风景”等无关词汇误判为大风）
WEATHER_KEYWORDS = [
    ('沙尘', '沙尘'), ('冰雹', '冰雹'), ('雷', '雷雨'), ('多云', '多云'), ('晴', '晴天'),
    ('阴', '阴天'), ('雨', '雨天'), ('雪', '雪天'), ('雾', '雾天'),
    ('大风', '大风'), ('狂风', '大风'), ('起风', '大风'),
]


def extract_weather(text):
    """从图片分析文本中提取天气标签"""
    if not text:
        return ''
    for kw, label in WEATHER_KEYWORDS:
        if kw in text:
            return label
    return ''


def resolve_gps_location(gps_entries):
    """从多张带 GPS 的照片中投票选出主要拍摄地（省·市众数）。

    gps_entries: [{'lat': float, 'lon': float, 'exif': dict}, ...]
    返回 (location, location_details, nearby_attractions, chosen_exif)
    """
    votes = Counter()
    best = {}
    for e in gps_entries:
        result = reverse_geocode(e['lat'], e['lon'])
        if not result:
            continue
        details = result.get('details') or {}
        province, city = extract_province_city(
            f"{details.get('province') or ''} {details.get('city') or ''}"
        )
        if not province and not city:
            province, city = extract_province_city(result.get('address') or '')
        key = format_location(province, city)
        if key == '未知地点':
            continue
        votes[key] += 1
        if key not in best:
            best[key] = {
                'address': result.get('address'),
                'details': details,
                'pois': result.get('pois'),
                'lat': e['lat'],
                'lon': e['lon'],
                'exif': e['exif'],
            }

    if not votes:
        return None, None, [], {}

    winner = votes.most_common(1)[0][0]
    info = best[winner]
    if info['pois']:
        nearby_attractions = [{'name': p.get('name'), 'address': p.get('address'), 'distance': p.get('distance')}
                              for p in info['pois'][:5]]
    else:
        nearby_attractions = get_nearby_attractions(info['lat'], info['lon'])
    return info['address'], info['details'], nearby_attractions, info['exif']


def safe_filename(filename):
    """对上传文件名做安全处理，避免路径穿越与重复覆盖"""
    name = os.path.basename(filename or '')
    # 仅保留中文、字母、数字、点、下划线、连字符
    name = re.sub(r'[^\w.\-一-鿿]', '_', name)
    if not name or name.startswith('.'):
        name = 'image'
    return f"{int(time.time() * 1000)}_{name}"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 40 * 1024 * 1024  # 40MB（多图上传）
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'shiguang-shouzhang-dev-secret-key')
app.config['JOURNALS_FILE'] = os.path.join(BASE_DIR, 'journals.json')  # 仅用于首次启动时的旧数据迁移

# 允许上传的图片扩展名
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

# 一次最多上传的图片数量
MAX_IMAGES = 9

# 确保上传目录存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 初始化 SQLite 数据库（用户表 + 手账表）
init_db()
# 首次启动：把旧的 journals.json 数据迁移到默认账号，实现平滑过渡
import_legacy_journals(app.config['JOURNALS_FILE'])


@app.after_request
def disable_html_cache(response):
    """开发阶段禁用页面缓存，避免浏览器使用旧的 HTML/JS 页面。"""
    if response.mimetype == 'text/html':
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    return response


# ===== 认证相关 =====
def current_user_id():
    return session.get('user_id')


def login_required(f):
    """未登录访问受保护接口时返回 401。"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user_id() is None:
            return jsonify({'error': '未登录'}), 401
        return f(*args, **kwargs)
    return wrapper


@app.route('/login')
def login():
    # 已登录则直接进入首页
    if current_user_id() is not None:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if len(username) < 2 or len(username) > 20:
        return jsonify({'error': '用户名长度需在 2~20 个字符之间'}), 400
    if len(password) < 6:
        return jsonify({'error': '密码长度至少 6 位'}), 400
    if get_user_by_username(username):
        return jsonify({'error': '该用户名已被注册'}), 409

    create_user(username, generate_password_hash(password))
    return jsonify({'message': '注册成功', 'username': username})


@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    user = get_user_by_username(username)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': '用户名或密码错误'}), 401

    session['user_id'] = user['id']
    return jsonify({'message': '登录成功', 'username': user['username']})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': '已退出登录'})


@app.route('/api/me')
def me():
    if current_user_id() is None:
        return jsonify({'logged_in': False})
    user = get_user_by_id(current_user_id())
    return jsonify({'logged_in': True, 'username': user['username'] if user else ''})


@app.route('/')
def index():
    if current_user_id() is None:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/journals', methods=['GET'])
@login_required
def get_journals():
    """获取当前用户的所有手账数据"""
    journals = list_journals(current_user_id())
    return jsonify(journals)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    # 兼容单图字段 file 与多图字段 files
    files = request.files.getlist('files')
    if not files:
        single = request.files.get('file')
        if single and single.filename:
            files = [single]

    files = [f for f in files if f and f.filename]
    if not files:
        return jsonify({'error': 'No file selected'}), 400

    if len(files) > MAX_IMAGES:
        return jsonify({'error': f'最多一次上传 {MAX_IMAGES} 张图片'}), 400

    # 校验文件类型，仅允许上传图片
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify({'error': '仅支持上传图片文件（jpg/jpeg/png/gif/webp/bmp）'}), 400

    # 读取用户补充的个性化信息（可选）
    mood = (request.form.get('mood') or '').strip()
    companions = (request.form.get('companions') or '').strip()
    custom_prompt = (request.form.get('custom_prompt') or '').strip()
    weather = (request.form.get('weather') or '').strip()
    tags_raw = (request.form.get('tags') or '').strip()
    tags = [t.strip() for t in re.split(r'[,，;；、\s]+', tags_raw) if t.strip()]

    # 保存所有文件并提取 EXIF
    saved = []
    for f in files:
        filename = safe_filename(f.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(filepath)
        saved.append({'filename': filename, 'path': filepath, 'exif': extract_exif(filepath)})

    # 地理位置：优先用带 GPS 的照片做省·市投票
    gps_entries = [
        {'lat': s['exif']['latitude'], 'lon': s['exif']['longitude'], 'exif': s['exif']}
        for s in saved
        if s['exif'].get('latitude') and s['exif'].get('longitude')
    ]
    location, location_details, nearby_attractions, chosen_exif = resolve_gps_location(gps_entries)

    # 主 EXIF：优先取定位成功的那张，否则取第一张（地图标记需要经纬度）
    exif_data = chosen_exif or saved[0]['exif']

    # 拍摄时间：取所有照片中最早的时间
    datetimes = [s['exif'].get('datetime') for s in saved if s['exif'].get('datetime')]
    created_at = min(datetimes) if datetimes else None

    # 视觉模型分析（逐张分析后合并，多图信息更充分）
    analyses = []
    for idx, s in enumerate(saved, start=1):
        analyses.append(f"【图片{idx}】\n{analyze_image(s['path'])}")
    image_analysis = "\n\n".join(analyses)

    # 从图片分析结果中提取天气（若用户未手动选择，则自动识别）
    if not weather:
        weather = extract_weather(image_analysis)

    # 生成旅游手账（整合用户个性化信息）
    journal = generate_travel_journal(
        image_analysis, location, created_at, nearby_attractions,
        mood=mood, companions=companions, weather=weather, custom_prompt=custom_prompt
    )

    # 提取省市信息（优先GPS逆地理编码结果，其次从文本识别）
    province, city = None, None
    if location_details:
        addr_province = location_details.get('province') or ''
        addr_city = location_details.get('city') or ''
        province, city = extract_province_city(f"{addr_province} {addr_city}")
    elif location:
        province, city = extract_province_city(location)

    # 若GPS信息不足，从手账文本和图片分析中提取
    if not province and not city:
        province, city = extract_province_city(f"{journal}\n{image_analysis}")

    extracted_location = format_location(province, city)

    print(f"Final extracted location: {extracted_location}")

    # 构建手账数据
    journal_data = {
        'id': '',
        'filename': saved[0]['filename'],
        'images': [s['filename'] for s in saved],
        'exif_data': exif_data,
        'location': extracted_location,
        'location_details': location_details,
        'nearby_attractions': nearby_attractions,
        'image_analysis': image_analysis,
        'journal': journal,
        'mood': mood,
        'companions': companions,
        'weather': weather,
        'tags': tags,
        'custom_prompt': custom_prompt,
        'created_at': created_at or time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(saved[0]['path'])))
    }

    # 保存手账数据（归属当前登录用户）
    create_journal(current_user_id(), journal_data)

    return jsonify(journal_data)

@app.route('/journals/<id>', methods=['DELETE'])
@login_required
def delete_journal(id):
    """删除当前用户的一篇手账，并清理其关联的图片文件"""
    journal = get_journal(current_user_id(), id)
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404

    deleted = delete_journal_row(current_user_id(), id)
    if not deleted:
        return jsonify({'error': 'Journal not found'}), 404

    # 删除该手账关联的图片文件，避免残留孤儿图片
    filenames = journal.get('images') or ([journal.get('filename')] if journal.get('filename') else [])
    for fn in filenames:
        if not fn:
            continue
        path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    return jsonify({'message': 'Journal deleted successfully'})

@app.route('/journals/<id>', methods=['PUT'])
@login_required
def update_journal(id):
    """修改当前用户的一篇手账"""
    journal = get_journal(current_user_id(), id)
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'journal' in data:
        journal['journal'] = data['journal']
    if 'location' in data:
        journal['location'] = data['location']
    if 'created_at' in data:
        journal['created_at'] = data['created_at']
    if 'mood' in data:
        journal['mood'] = (data['mood'] or '').strip()
    if 'companions' in data:
        journal['companions'] = (data['companions'] or '').strip()
    if 'weather' in data:
        journal['weather'] = (data['weather'] or '').strip()
    if 'tags' in data:
        raw = data['tags']
        if isinstance(raw, str):
            journal['tags'] = [t.strip() for t in re.split(r'[,，;；、\s]+', raw) if t.strip()]
        elif isinstance(raw, list):
            journal['tags'] = [str(t).strip() for t in raw if str(t).strip()]
        else:
            journal['tags'] = []

    update_journal_row(current_user_id(), id, journal)
    return jsonify(journal)

@app.route('/journals/<id>/export/image', methods=['GET'])
@login_required
def export_image(id):
    """将手账导出为长图（PNG）"""
    journal = get_journal(current_user_id(), id)
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404
    buf = journal_image_bytes(journal, app.config['UPLOAD_FOLDER'])
    return send_file(buf, mimetype='image/png', as_attachment=True,
                     download_name=f'journal_{id}.png')

@app.route('/journals/<id>/export/pdf', methods=['GET'])
@login_required
def export_pdf(id):
    """将手账导出为 PDF"""
    journal = get_journal(current_user_id(), id)
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404
    buf = journal_pdf_bytes(journal, app.config['UPLOAD_FOLDER'])
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f'journal_{id}.pdf')

@app.errorhandler(413)
def too_large(e):
    """文件总大小超限时返回友好错误"""
    return jsonify({'error': '图片总大小不能超过 40MB'}), 413

if __name__ == '__main__':
    app.run(debug=True)
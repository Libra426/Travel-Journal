# -*- coding: utf-8 -*-
"""生成「时光手账」项目的 UML 图（PNG，2x 高清）。
运行：python pic/generate_diagrams.py
输出到 pic/ 目录：类图、活动图、顺序图、用例图、状态图。

使用 Pillow 直接绘制，依赖系统中文字体（Microsoft YaHei）。
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

# ---------- 通用 ----------
CREAM = "#FDF8F3"
BOX = "#FFFEFA"
SAGE = "#A8B5A8"
SAGE_LIGHT = "#C5D5C5"
TERRA = "#D4A59A"
BLUSH = "#F5E6E0"
TEXT = "#4A4A4A"
MUTED = "#8A8A8A"
LINE = "#B9B0A6"

SCALE = 2  # 输出 2x 高清

_FONT_DIR = r"C:\Windows\Fonts"
_FONT_REGULAR = os.path.join(_FONT_DIR, "msyh.ttc")
_FONT_BOLD = os.path.join(_FONT_DIR, "msyhbd.ttc")


def _load_font(path, px_size):
    for p in (path, _FONT_REGULAR, os.path.join(_FONT_DIR, "simhei.ttf")):
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, px_size)
            except Exception:
                continue
    return ImageFont.load_default()


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.img = Image.new("RGB", (int(w * SCALE), int(h * SCALE)), CREAM)
        self.d = ImageDraw.Draw(self.img)
        self._fonts = {}

    def _c(self, v):
        return v * SCALE

    def _f(self, size, bold=False):
        key = (int(round(size * SCALE)), bool(bold))
        if key not in self._fonts:
            self._fonts[key] = _load_font(_FONT_BOLD if bold else _FONT_REGULAR, key[0])
        return self._fonts[key]

    def _dash(self, dash):
        return [int(x) * SCALE for x in dash.split(",")]

    def _arrowhead(self, p1, p2, color, filled):
        x1, y1 = p1
        x2, y2 = p2
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return
        ux, uy = dx / L, dy / L
        A = 9 * SCALE      # 箭头长度
        W = 3.5 * SCALE    # 半宽
        bx, by = x2 - ux * A, y2 - uy * A
        px, py = -uy, ux
        lx, ly = bx + px * W, by + py * W
        rx, ry = bx - px * W, by - py * W
        if filled:
            self.d.polygon([(x2, y2), (lx, ly), (rx, ry)], fill=color)
        else:
            self.d.line([(x2, y2), (lx, ly)], fill=color, width=max(1, int(1.2 * SCALE)))
            self.d.line([(x2, y2), (rx, ry)], fill=color, width=max(1, int(1.2 * SCALE)))

    def _draw_dashed(self, pts, color, width, dash):
        on, off = dash[0], dash[1]
        if on <= 0:
            return
        pen_down = True
        remaining = on
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            seg = math.hypot(x2 - x1, y2 - y1)
            if seg < 1e-6:
                continue
            ux, uy = (x2 - x1) / seg, (y2 - y1) / seg
            pos = 0.0
            while pos < seg:
                step = min(remaining, seg - pos)
                nx, ny = x1 + ux * (pos + step), y1 + uy * (pos + step)
                if pen_down:
                    self.d.line([(x1 + ux * pos, y1 + uy * pos), (nx, ny)], fill=color, width=width)
                pos += step
                pen_down = not pen_down
                remaining = on if pen_down else off

    def _rounded_perimeter(self, x, y, w, h, r):
        x0, y0, x1, y1 = x, y, x + w, y + h
        pts = []

        def arc(cx, cy, rr, a0, a1, steps=16):
            out = []
            for i in range(steps + 1):
                a = math.radians(a0 + (a1 - a0) * i / steps)
                out.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
            return out

        pts.append((x0 + r, y0))
        pts.append((x1 - r, y0))
        pts += arc(x1 - r, y0 + r, r, -90, 0)
        pts.append((x1, y0 + r))
        pts.append((x1, y1 - r))
        pts += arc(x1 - r, y1 - r, r, 0, 90)
        pts.append((x1 - r, y1))
        pts.append((x0 + r, y1))
        pts += arc(x0 + r, y1 - r, r, 90, 180)
        pts.append((x0, y1 - r))
        pts.append((x0, y0 + r))
        pts += arc(x0 + r, y0 + r, r, 180, 270)
        return [(self._c(px), self._c(py)) for px, py in pts]

    # ---- 基础图形 ----
    def rect(self, x, y, w, h, fill=BOX, stroke=LINE, r=6, sw=1.2, dash=None):
        x0, y0 = self._c(x), self._c(y)
        x1, y1 = self._c(x + w), self._c(y + h)
        rr = self._c(r)
        swpx = max(1, int(round(sw * SCALE)))
        if fill and fill != "none":
            self.d.rounded_rectangle([x0, y0, x1, y1], radius=rr, fill=fill)
        if stroke and stroke != "none":
            if dash:
                self._draw_dashed(self._rounded_perimeter(x, y, w, h, r), stroke, swpx, self._dash(dash))
            else:
                self.d.rounded_rectangle([x0, y0, x1, y1], radius=rr, outline=stroke, width=swpx)

    def ellipse(self, cx, cy, rx, ry, fill=BOX, stroke=SAGE, sw=1.3):
        x0, y0 = self._c(cx - rx), self._c(cy - ry)
        x1, y1 = self._c(cx + rx), self._c(cy + ry)
        self.d.ellipse([x0, y0, x1, y1], fill=fill, outline=stroke,
                       width=max(1, int(round(sw * SCALE))))

    def polygon(self, pts, fill=BOX, stroke=SAGE, sw=1.3):
        pp = [(self._c(x), self._c(y)) for x, y in pts]
        self.d.polygon(pp, fill=fill, outline=stroke, width=max(1, int(round(sw * SCALE))))

    def text(self, x, y, s, size=13, fill=TEXT, anchor="start", bold=False):
        font = self._f(size, bold)
        a = {"start": "ls", "middle": "ms", "end": "rs"}.get(anchor, "ls")
        self.d.text((self._c(x), self._c(y)), str(s), font=font, fill=fill, anchor=a)

    def line(self, x1, y1, x2, y2, stroke=LINE, sw=1.2, dash=None, marker=None):
        p1 = (self._c(x1), self._c(y1))
        p2 = (self._c(x2), self._c(y2))
        w = max(1, int(round(sw * SCALE)))
        if dash:
            self._draw_dashed([p1, p2], stroke, w, self._dash(dash))
        else:
            self.d.line([p1, p2], fill=stroke, width=w)
        if marker:
            self._arrowhead(p1, p2, stroke, filled=(marker == "arr"))

    def polyline(self, pts, stroke=LINE, sw=1.2, dash=None, marker=None, fill="none"):
        pp = [(self._c(x), self._c(y)) for x, y in pts]
        w = max(1, int(round(sw * SCALE)))
        if dash:
            self._draw_dashed(pp, stroke, w, self._dash(dash))
        else:
            self.d.line(pp, fill=stroke, width=w, joint="curve")
        if marker and len(pp) >= 2:
            self._arrowhead(pp[-2], pp[-1], stroke, filled=(marker == "arr"))

    def rect_text_center(self, x, y, w, h, s, size=13, fill=TEXT, bold=False):
        lines = str(s).split("\n")
        if len(lines) == 1:
            self.text(x + w / 2, y + h / 2 + size * 0.35, lines[0], size=size, fill=fill, anchor="middle", bold=bold)
            return
        line_h = size * 1.4
        total = line_h * len(lines)
        start_y = y + (h - total) / 2 + size * 0.8
        for i, ln in enumerate(lines):
            self.text(x + w / 2, start_y + i * line_h, ln, size=size, fill=fill, anchor="middle", bold=bold)

    def title(self, text, y):
        self.text(self.w / 2, y, text, size=24, fill=TEXT, anchor="middle", bold=True)

    def subtitle(self, text, y):
        self.text(self.w / 2, y, text, size=13, fill=MUTED, anchor="middle")

    def class_box(self, x, y, w, name, attrs, methods):
        """UML 类框：名称 + 属性 + 方法。返回框高。"""
        H = 32
        R = 21
        DIV = 8
        h = H + len(attrs) * R + (DIV if methods else 0) + len(methods) * R
        self.rect(x, y, w, h, fill=BOX, stroke=SAGE, sw=1.3)
        self.rect(x, y, w, H, fill=SAGE, stroke=SAGE, sw=1.3, r=6)
        self.rect(x, y + H - 6, w, 6, fill=SAGE, stroke="none")
        self.text(x + w / 2, y + H / 2 + 5, name, size=14, fill="#FFFFFF", anchor="middle", bold=True)
        yy = y + H
        for a in attrs:
            yy += R
            self.text(x + 12, yy - 5, a, size=12.5, fill=TEXT)
        if methods:
            yy += DIV
            self.line(x, yy, x + w, yy, stroke=SAGE, sw=1)
            for m in methods:
                yy += R
                self.text(x + 12, yy - 5, m, size=12.5, fill=TEXT)
        return h

    def save(self, path):
        self.img.save(path, "PNG")


OUT = os.path.dirname(os.path.abspath(__file__))


# =====================================================================
# 1) 类图
# =====================================================================
def class_diagram():
    s = Canvas(1600, 1000)
    s.title("时光手账系统 —— 类图 (Class Diagram)", 46)
    s.subtitle("Flask 主应用 + 工具模块 + 用户/手账数据模型（SQLite 持久化）", 70)

    app_attrs = [
        "- UPLOAD_FOLDER : str",
        "- MAX_CONTENT_LENGTH : int (40MB)",
        "- MAX_IMAGES : int (9)",
        "- SECRET_KEY : str",
        "- JOURNALS_FILE : str (旧数据迁移)",
    ]
    app_meth = [
        "+ register() : json", "+ login_api() : json", "+ logout() : json",
        "+ get_journals() : json", "+ upload() : json",
        "+ update_journal(id) : json", "+ delete_journal(id) : json",
        "+ export_image(id) : file", "+ export_pdf(id) : file",
    ]
    app_h = s.class_box(40, 110, 600, "App (app.py)", app_attrs, app_meth)

    # 数据模型包（SQLite 两张表对应的模型）
    s.rect(1140, 90, 420, 540, fill="#FBFAF6", stroke=SAGE_LIGHT, sw=1.6, dash="7,5", r=14)
    s.text(1160, 115, "数据模型 (SQLite)", size=14, fill=SAGE, bold=True)

    jattrs = [
        "id : str", "filename : str", "images : list", "exif_data : dict",
        "location : str", "location_details : dict", "nearby_attractions : list",
        "image_analysis : str", "journal : str", "mood : str", "companions : str",
        "weather : str", "tags : list", "custom_prompt : str", "created_at : str",
    ]
    s.class_box(1160, 130, 380, "Journal (journals 表)", jattrs, [])

    uattrs = ["id : int (主键)", "username : str (唯一)", "password_hash : str", "created_at : str"]
    s.class_box(1160, 495, 380, "User (users 表)", uattrs, [])

    # 工具模块包
    s.rect(40, 700, 1520, 300, fill="#FBFAF6", stroke=SAGE_LIGHT, sw=1.6, dash="7,5", r=14)
    s.text(60, 725, "工具模块 (utils)", size=14, fill=SAGE, bold=True)

    db_meth = [
        "+ init_db()", "+ create_user(username, hash)", "+ get_user_by_username(name)",
        "+ get_user_by_id(id)", "+ list_journals(user_id)", "+ get_journal(user_id, id)",
        "+ create_journal(user_id, data)", "+ update_journal_row(...)",
        "+ delete_journal_row(...)", "+ import_legacy_journals(...)",
    ]
    s.class_box(60, 745, 235, "Database (database.py)", [], db_meth)
    s.class_box(310, 745, 235, "ExifExtractor", [],
                ["+ extract_exif(path): dict", "+ convert_to_degrees(v)",
                 "+ validate_coordinates(..)", "+ get_if_exist(data, key)"])
    s.class_box(560, 745, 235, "BaiduMap", ["- BAIDU_API_KEY : str"],
                ["+ reverse_geocode(lat, lon)", "+ get_nearby_attractions(..)",
                 "+ reverse_geocode_amap(..)", "+ wgs84_to_bd09(..)"])
    s.class_box(810, 745, 235, "VisionModel", ["- VISION_API_KEY", "- VISION_MODEL"],
                ["+ analyze_image(path): str", "+ encode_image(path)"])
    s.class_box(1060, 745, 235, "TextModel", ["- TEXT_API_KEY", "- TEXT_MODEL"],
                ["+ generate_travel_journal(..): str"])
    s.class_box(1310, 745, 235, "Exporter", [],
                ["+ journal_image_bytes(..)", "+ journal_pdf_bytes(..)",
                 "+ render_journal_image(..)", "+ clean_text(text)", "+ wrap_text(..)"])

    # App -> 工具模块（依赖）
    s.polyline([(340, 110 + app_h), (340, 700)], stroke=TEXT, dash="5,4", marker="dep")
    s.text(350, 590, "依赖 (import utils.*)", size=11, fill=MUTED)

    # App -> 数据模型（创建/返回手账）
    s.line(640, 300, 1140, 300, stroke=TEXT, sw=1.2, dash="5,4", marker="dep")
    s.text(890, 290, "创建 / 返回手账数据", size=11, fill=MUTED, anchor="middle")

    # Database -> 数据模型（SQLite 读写）
    s.polyline([(295, 760), (1140, 630)], stroke=TEXT, sw=1.2, dash="5,4", marker="dep")
    s.text(720, 725, "SQLite 读写 (users / journals 表)", size=11, fill=MUTED)

    return s


# =====================================================================
# 2) 活动图
# =====================================================================
def activity_diagram():
    s = Canvas(900, 1320)
    s.title("时光手账系统 —— 活动图 (Activity Diagram)", 46)
    s.subtitle("用户上传图片并生成手账的完整业务流程", 70)
    cx = 450

    def act(cx, y, label, w=240, fill=BOX):
        s.rect(cx - w / 2, y, w, 40, fill=fill, stroke=SAGE, sw=1.3, r=20)
        s.rect_text_center(cx - w / 2, y, w, 40, label, size=13)
        return y + 40

    def decision(cx, y, label):
        s.polygon([(cx, y - 26), (cx + 60, y), (cx, y + 26), (cx - 60, y)])
        s.text(cx, y + 5, label, size=12, anchor="middle", fill=TEXT)
        return y

    def arrow(x1, y1, x2, y2):
        s.line(x1, y1, x2, y2, stroke=TEXT, sw=1.3, marker="arr")

    # 开始
    s.rect(cx - 9, 90, 18, 18, fill=TEXT, stroke=TEXT, r=9)
    arrow(cx, 108, cx, 130)
    y = act(cx, 130, "选择 / 拖拽图片（最多 9 张）", w=250)
    arrow(cx, y, cx, y + 26)
    dy = decision(cx, y + 52, "≤ 40MB ?")
    # 否
    s.text(cx - 200, dy - 6, "否", size=11, fill=TERRA, anchor="middle")
    s.polyline([(cx - 60, dy), (cx - 290, dy), (cx - 290, dy + 40)], stroke=TEXT, marker="arr")
    act(cx - 290, dy + 40, "提示“超过 40MB”", w=200, fill=BLUSH)
    # 是
    s.text(cx + 95, dy - 6, "是", size=11, fill=SAGE, anchor="middle")
    arrow(cx + 60, dy, cx + 60, dy + 60)
    y2 = act(cx, dy + 60, "打开个性化设置（可选）", w=250)
    arrow(cx + 60, y2, cx + 60, y2 + 24)
    y3 = act(cx, y2 + 24, "填写心情 / 同行人 / 标签 / 天气 / 提示词", w=350)
    arrow(cx, y3, cx, y3 + 26)
    y4 = act(cx, y3 + 26, "POST /upload 上传图片与个性化信息", w=320)
    arrow(cx, y4, cx, y4 + 26)
    d4 = decision(cx, y4 + 52, "图片类型合法 ?")
    s.text(cx + 95, d4 - 6, "是", size=11, fill=SAGE, anchor="middle")
    s.text(cx - 200, d4 - 6, "否", size=11, fill=TERRA, anchor="middle")
    s.polyline([(cx - 60, d4), (cx - 290, d4), (cx - 290, d4 + 40)], stroke=TEXT, marker="arr")
    act(cx - 290, d4 + 40, "返回错误 400", w=180, fill=BLUSH)
    arrow(cx + 60, d4, cx + 60, d4 + 60)
    y5 = act(cx, d4 + 60, "保存图片到 static/uploads", w=300)
    arrow(cx + 60, y5, cx + 60, y5 + 26)
    y6 = act(cx, y5 + 26, "提取 EXIF 信息", w=200)
    arrow(cx, y6, cx, y6 + 26)
    d6 = decision(cx, y6 + 52, "含 GPS ?")
    s.text(cx + 95, d6 - 6, "是", size=11, fill=SAGE, anchor="middle")
    s.text(cx - 128, d6 - 6, "否", size=11, fill=TERRA, anchor="middle")
    s.polyline([(cx + 60, d6), (cx + 170, d6), (cx + 170, d6 + 40)], stroke=TEXT, marker="arr")
    act(cx + 170, d6 + 40, "逆地理编码 + 省·市投票\n获取地址 + 附近景点", w=210)
    s.polyline([(cx - 60, d6), (cx - 170, d6), (cx - 170, d6 + 40)], stroke=TEXT)
    join_y = d6 + 100
    s.polyline([(cx - 170, d6 + 40), (cx - 170, join_y), (cx, join_y)], stroke=TEXT)
    s.polyline([(cx + 170, d6 + 40), (cx + 170, join_y), (cx, join_y)], stroke=TEXT)
    arrow(cx, join_y, cx, join_y + 26)
    y7 = act(cx, join_y + 26, "视觉大模型逐张分析图片", w=260)
    arrow(cx, y7, cx, y7 + 26)
    y8 = act(cx, y7 + 26, "提取天气（未手动选择则自动识别）", w=300)
    arrow(cx, y8, cx, y8 + 26)
    y9 = act(cx, y8 + 26, "文本大模型生成游记文案", w=260)
    arrow(cx, y9, cx, y9 + 26)
    y10 = act(cx, y9 + 26, "提取省市（GPS 优先 / 关键词兜底）", w=320)
    arrow(cx, y10, cx, y10 + 26)
    y11 = act(cx, y10 + 26, "保存手账到数据库 SQLite", w=260)
    arrow(cx, y11, cx, y11 + 26)
    y12 = act(cx, y11 + 26, "前端更新手账列表 + 足迹地图", w=300)
    arrow(cx, y12, cx, y12 + 30)
    s.rect(cx - 12, y12 + 30, 24, 24, fill="none", stroke=TEXT, sw=1.5, r=12)
    s.rect(cx - 7, y12 + 35, 14, 14, fill=TEXT, r=7)
    s.text(cx + 26, y12 + 48, "结束", size=11, fill=MUTED)
    return s


# =====================================================================
# 3) 顺序图
# =====================================================================
def sequence_diagram():
    s = Canvas(1400, 840)
    s.title("时光手账系统 —— 顺序图 (Sequence Diagram)", 46)
    s.subtitle("用户登录后上传照片生成手账的调用时序", 70)

    lifelines = [
        ("用户", 60), ("前端", 210), ("后端 app.py", 390), ("ExifExtractor", 570),
        ("BaiduMap", 770), ("VisionModel", 950), ("TextModel", 1130), ("Database", 1310),
    ]
    top = 100
    for name, x in lifelines:
        s.rect(x - 55, top, 110, 32, fill=SAGE, stroke=SAGE, r=8)
        s.rect_text_center(x - 55, top, 110, 32, name, size=12, fill="#FFFFFF", bold=True)
        s.line(x, top + 32, x, 790, stroke=LINE, sw=1, dash="4,4")

    def msg(x1, x2, y, label, ret=False):
        s.line(x1, y, x2, y, stroke=TEXT if not ret else MUTED, sw=1.3,
               dash=None if not ret else "5,4", marker="arr")
        s.text((x1 + x2) / 2, y - 6, label, size=12, fill=TEXT if not ret else MUTED, anchor="middle")

    def selfmsg(x, y, h, label):
        s.polyline([(x, y), (x + 90, y), (x + 90, y + h), (x, y + h)], stroke=TEXT, marker="arr")
        s.text(x + 100, y + h / 2, label, size=11, fill=MUTED)

    y = 150
    msg(60, 210, y, "1. 登录 / 注册")
    y += 26
    msg(210, 390, y, "2. POST /api/login (用户名, 密码)")
    y += 26
    msg(390, 210, y, "3. 登录成功 (session)", ret=True)
    y += 26
    msg(60, 210, y, "4. 选择图片 + 填写心情/同行人/标签")
    y += 26
    selfmsg(210, y, 22, "校验 ≤40MB & 类型")
    y += 40
    msg(210, 390, y, "5. POST /upload (多图 + 个性化字段)")
    y += 26
    selfmsg(390, y, 22, "校验类型 & 保存文件")
    y += 40
    msg(390, 570, y, "6. extract_exif(path)")
    y += 24
    msg(570, 390, y, "exif_data (经纬度/时间)", ret=True)
    y += 26
    msg(390, 770, y, "7. reverse_geocode(lat, lon)")
    y += 24
    msg(770, 390, y, "地址 + POI 兴趣点", ret=True)
    y += 26
    msg(390, 770, y, "8. get_nearby_attractions(lat, lon)")
    y += 24
    msg(770, 390, y, "附近景点列表", ret=True)
    y += 26
    msg(390, 950, y, "9. analyze_image(path) ×N 逐张")
    y += 24
    msg(950, 390, y, "image_analysis", ret=True)
    y += 26
    msg(390, 1130, y, "10. generate_travel_journal(分析,位置,时间,景点,心情…)")
    y += 24
    msg(1130, 390, y, "小红书风格游记文案", ret=True)
    y += 26
    msg(390, 1310, y, "11. create_journal(user_id, data)")
    y += 24
    msg(1310, 390, y, "保存成功 (id)", ret=True)
    y += 26
    msg(390, 210, y, "12. 返回 journal_data (JSON)", ret=True)
    y += 26
    selfmsg(210, y, 22, "更新列表 & 足迹地图")
    return s


# =====================================================================
# 4) 用例图
# =====================================================================
def usecase_diagram():
    s = Canvas(1500, 920)
    s.title("时光手账系统 —— 用例图 (Use Case Diagram)", 46)
    s.subtitle("系统边界与用户 / 外部服务交互", 70)

    # 系统边界
    s.rect(260, 110, 1040, 720, fill="#FBFAF6", stroke=SAGE_LIGHT, sw=1.6, dash="7,5", r=14)
    s.text(282, 136, "时光手账系统", size=15, fill=SAGE, anchor="start", bold=True)

    def actor(x, y, label):
        s.rect(x - 8, y - 28, 16, 16, fill=BLUSH, stroke=TERRA, r=8)
        s.line(x, y - 12, x, y + 16, stroke=TERRA, sw=1.5)
        s.line(x, y - 6, x - 16, y + 8, stroke=TERRA, sw=1.5)
        s.line(x, y - 6, x + 16, y + 8, stroke=TERRA, sw=1.5)
        s.line(x, y + 16, x - 14, y + 34, stroke=TERRA, sw=1.5)
        s.line(x, y + 16, x + 14, y + 34, stroke=TERRA, sw=1.5)
        s.text(x, y + 52, label, size=13, fill=TEXT, anchor="middle", bold=True)

    def uc(cx, cy, label, w=170):
        s.ellipse(cx, cy, w / 2, 28)
        s.text(cx, cy + 5, label, size=12.5, anchor="middle", fill=TEXT)
        return cx, cy

    def assoc(x1, y1, x2, y2):
        s.line(x1, y1, x2, y2, stroke=TEXT, sw=1.3)

    def include(x1, y1, x2, y2):
        s.line(x1, y1, x2, y2, stroke=TERRA, sw=1.2, dash="5,4", marker="dep")
        s.text((x1 + x2) / 2 - 30, (y1 + y2) / 2 - 4, "«include»", size=10, fill=TERRA)

    # 参与者
    actor(120, 460, "用户")
    actor(1400, 220, "视觉大模型")
    actor(1400, 360, "地图服务")
    actor(1400, 500, "文本大模型")

    # 用例 —— 用户（左侧）
    uc(390, 190, "注册", 150)
    uc(390, 300, "登录", 150)
    uc(390, 410, "退出登录", 170)
    uc(390, 540, "查看手账", 150)
    uc(390, 640, "检索手账", 150)
    uc(390, 740, "修改 / 删除手账", 190)
    uc(650, 620, "导出手账（长图/PDF）", 210)
    uc(650, 730, "足迹地图可视化", 190)
    uc(650, 210, "上传图片·生成手账", 190)

    # 用例 —— 外部服务（右侧）
    uc(1000, 220, "图片内容识别", 170)
    uc(1000, 360, "地理位置定位", 170)
    uc(1000, 500, "生成手账文案", 170)

    # 用户关联（普通连线）
    for (ux, uy) in [(390, 190), (390, 300), (390, 410), (390, 540), (390, 640),
                     (390, 740), (650, 620), (650, 730), (650, 210)]:
        assoc(120, 460, ux, uy)

    # include：上传图片 -> 三个子流程
    include(650, 240, 915, 235)
    include(650, 240, 915, 360)
    include(650, 240, 915, 500)

    # 外部服务关联
    assoc(1380, 220, 1090, 220)   # 视觉大模型 -> 图片内容识别
    assoc(1380, 360, 1090, 360)   # 地图服务 -> 地理位置定位
    assoc(1380, 500, 1090, 500)   # 文本大模型 -> 生成手账文案

    return s


# =====================================================================
# 5) 状态图
# =====================================================================
def state_diagram():
    s = Canvas(980, 760)
    s.title("时光手账系统 —— 状态图 (State Diagram)", 46)
    s.subtitle("手账记录的生命周期状态", 70)

    def state(cx, cy, w, h, name):
        s.rect(cx - w / 2, cy - h / 2, w, h, fill=BOX, stroke=SAGE, sw=1.4, r=12)
        s.rect_text_center(cx - w / 2, cy - h / 2, w, h, name, size=13.5, bold=True)

    def trans(x1, y1, x2, y2, label, lx=None, ly=None, dash=None, color=TEXT):
        s.line(x1, y1, x2, y2, stroke=color, sw=1.3, dash=dash, marker="arr")
        if label:
            lx = (x1 + x2) / 2 + 8 if lx is None else lx
            ly = (y1 + y2) / 2 - 4 if ly is None else ly
            s.text(lx, ly, label, size=11, fill=MUTED)

    # 初始
    s.rect(60 - 9, 100 - 9, 18, 18, fill=TEXT, r=9)
    s.line(60, 109, 60, 138, stroke=TEXT, marker="arr")

    state(190, 175, 220, 62, "未上传（空闲）")
    state(190, 310, 220, 62, "已选择图片")
    state(190, 445, 220, 62, "处理中")
    state(190, 580, 220, 62, "已生成手账")
    state(560, 580, 200, 62, "编辑中")

    # 终态
    s.rect(190 - 14, 690 - 14, 28, 28, fill="none", stroke=TEXT, sw=1.6, r=14)
    s.rect(190 - 9, 690 - 9, 18, 18, fill=TEXT, r=9)

    trans(60, 147, 80, 175, "无记录", lx=30, ly=158)
    trans(190, 206, 190, 279, "选择图片")
    trans(190, 341, 190, 414, "确认生成 / 直接生成")
    trans(190, 476, 190, 549, "生成完成")
    trans(190, 611, 190, 662, "删除手账")

    # 取消：已选择图片 -> 未上传
    s.polyline([(80, 290), (40, 290), (40, 175)], stroke=MUTED, dash="4,4", marker="arr")
    s.text(46, 240, "取消 / 关闭弹窗", size=10.5, fill=MUTED)

    # 已生成 <-> 编辑中
    trans(300, 580, 460, 580, "点击“修改”")
    trans(460, 600, 300, 600, "保存 / 取消", lx=340, ly=618)

    # 处理失败回退
    s.polyline([(300, 445), (430, 445), (430, 310), (300, 310)], stroke=TERRA, dash="4,4", marker="arr")
    s.text(445, 385, "处理失败", size=10.5, fill=TERRA)
    return s


if __name__ == "__main__":
    for name, fn in [("class-diagram", class_diagram),
                     ("activity-diagram", activity_diagram),
                     ("sequence-diagram", sequence_diagram),
                     ("use-case-diagram", usecase_diagram),
                     ("state-diagram", state_diagram)]:
        canvas = fn()
        canvas.save(os.path.join(OUT, name + ".png"))
        print("wrote", name + ".png", f"({canvas.w * SCALE}x{canvas.h * SCALE})")
    print("全部生成完毕。")

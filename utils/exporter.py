"""手账导出工具：将完整手账内容渲染为长图，并支持封装为 PDF。

使用 Pillow + 系统中文字体绘制，不依赖浏览器/额外服务。
中文字体渲染中文/ASCII，Segoe UI Emoji 字体渲染 emoji（黑白描边，Pillow 不支持彩色 emoji）。
"""
import io
import os
from PIL import Image, ImageDraw, ImageFont

# Windows 中文字体
_FONT_DIR = r'C:\Windows\Fonts'
_FONT_REGULAR_PATHS = [
    os.path.join(_FONT_DIR, 'msyh.ttc'),
    os.path.join(_FONT_DIR, 'simhei.ttf'),
]
_FONT_BOLD_PATHS = [
    os.path.join(_FONT_DIR, 'msyhbd.ttc'),
    os.path.join(_FONT_DIR, 'msyh.ttc'),
    os.path.join(_FONT_DIR, 'simhei.ttf'),
]
# Windows emoji 字体（用于导出时渲染 emoji，避免被直接丢弃）
_EMOJI_FONT_PATHS = [
    os.path.join(_FONT_DIR, 'seguiemj.ttf'),
    os.path.join(_FONT_DIR, 'seguisym.ttf'),
]


def _load_font(paths, size):
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _is_emoji(ch):
    """判断字符是否需要 emoji 字体渲染（非中文/ASCII/常见标点即视为 emoji）。"""
    cp = ord(ch)
    if 0x20 <= cp <= 0x7E:        # ASCII 可打印
        return False
    if 0x2000 <= cp <= 0x206F:    # 通用标点（— – … 等）
        return False
    if 0x3000 <= cp <= 0x303F:    # CJK 标点
        return False
    if 0x4E00 <= cp <= 0x9FFF:    # CJK 汉字
        return False
    if 0xFF00 <= cp <= 0xFFEF:    # 全角字符
        return False
    return True


def _run_font(ch, normal, emoji):
    return emoji if (emoji is not None and _is_emoji(ch)) else normal


def _text_len(draw, text, normal, emoji):
    total = 0.0
    for ch in text:
        total += draw.textlength(ch, font=_run_font(ch, normal, emoji))
    return total


def _draw_text(draw, xy, text, normal, emoji, fill):
    """按字符选择字体绘制，使 emoji 与中文混排时都能正确显示。"""
    x, y = xy
    for ch in text:
        f = _run_font(ch, normal, emoji)
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f)


def clean_text(text):
    """过滤掉控制字符（保留 emoji、中文、ASCII 与常见标点）。"""
    if not text:
        return ''
    out = []
    for ch in text:
        cp = ord(ch)
        if ch in ('\n', '\t'):
            out.append(ch)
        elif cp < 0x20 or cp == 0x7F:    # 控制字符
            continue
        else:
            out.append(ch)
    return ''.join(out)


def wrap_text(draw, text, normal, emoji, max_width):
    """按像素宽度对文本（含中文/emoji）进行换行。"""
    lines = []
    for paragraph in text.split('\n'):
        paragraph = paragraph.rstrip()
        if not paragraph:
            lines.append('')
            continue
        current = ''
        for ch in paragraph:
            test = current + ch
            if _text_len(draw, test, normal, emoji) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def _meta_lines(journal):
    """构建元信息行列表 [(文本, 是否加粗)]"""
    rows = []
    created_at = journal.get('created_at') or ''
    location = journal.get('location') or ''
    rows.append((f"拍摄时间：{created_at}" if created_at else "拍摄时间：未知", False))
    rows.append((f"地点：{location}" if location else "地点：未知地点", False))
    if journal.get('mood'):
        rows.append((f"心情：{journal['mood']}", False))
    if journal.get('companions'):
        rows.append((f"同行人：{journal['companions']}", False))
    if journal.get('weather'):
        rows.append((f"天气：{journal['weather']}", False))
    tags = journal.get('tags')
    if tags:
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.replace('，', ',').split(',') if t.strip()]
        if tags:
            rows.append((f"标签：{'、'.join(tags)}", False))
    return rows


def render_journal_image(journal, upload_folder):
    """将一篇手账渲染为纵向长图，返回 PIL Image。"""
    W = 720
    PAD = 40
    CW = W - 2 * PAD  # 内容宽度

    raw = journal.get('journal') or ''
    lines = raw.split('\n')
    title = clean_text(lines[0].strip()) if lines else '旅行手账'
    body = clean_text('\n'.join(lines[1:]).strip())

    font_title = _load_font(_FONT_BOLD_PATHS, 34)
    font_body = _load_font(_FONT_REGULAR_PATHS, 26)
    font_meta = _load_font(_FONT_REGULAR_PATHS, 21)
    emoji_title = _load_font(_EMOJI_FONT_PATHS, 34)
    emoji_body = _load_font(_EMOJI_FONT_PATHS, 26)
    emoji_meta = _load_font(_EMOJI_FONT_PATHS, 21)

    # 度量（临时画布）
    dummy = Image.new('RGB', (10, 10))
    dd = ImageDraw.Draw(dummy)
    title_lines = wrap_text(dd, title, font_title, emoji_title, CW)
    body_lines = wrap_text(dd, body, font_body, emoji_body, CW)
    meta_rows = _meta_lines(journal)
    meta_rows = [(clean_text(t), b) for t, b in meta_rows]

    line_h_title = int(font_title.size * 1.5)
    line_h_body = int(font_body.size * 1.7)
    line_h_meta = int(font_meta.size * 1.6)

    # 加载并缩放图片（支持多图）
    photos = []
    filenames = journal.get('images')
    if not filenames:
        filename = journal.get('filename')
        filenames = [filename] if filename else []
    for fn in filenames:
        if not fn:
            continue
        photo_path = os.path.join(upload_folder, fn)
        if not os.path.exists(photo_path):
            continue
        try:
            p = Image.open(photo_path).convert('RGB')
        except Exception:
            continue
        pw, ph = p.size
        target_w = CW
        target_h = int(ph * target_w / pw)
        if target_h > 460:
            target_h = 460
            target_w = int(pw * target_h / ph)
        photos.append(p.resize((target_w, target_h)))

    # 计算总高度
    total = PAD
    total += len(title_lines) * line_h_title
    total += 18
    for _ in meta_rows:
        total += line_h_meta + 4
    total += 24
    if photos:
        total += sum(p.height for p in photos) + 24 * len(photos)
    total += len(body_lines) * line_h_body
    total += PAD

    img = Image.new('RGB', (W, total), '#FFFEFA')
    d = ImageDraw.Draw(img)

    y = PAD
    # 标题
    for line in title_lines:
        _draw_text(d, (PAD, y), line, font_title, emoji_title, '#5D5D5D')
        y += line_h_title
    y += 18

    # 分隔线
    d.line([(PAD, y - 10), (W - PAD, y - 10)], fill='#E8E0D8', width=1)

    # 元信息
    for text, _ in meta_rows:
        _draw_text(d, (PAD, y), text, font_meta, emoji_meta, '#8A8A8A')
        y += line_h_meta + 4
    y += 20

    # 图片（居中，多张依次排列）
    for p in photos:
        x = (W - p.width) // 2
        img.paste(p, (x, y))
        y += p.height + 24

    # 正文
    for line in body_lines:
        _draw_text(d, (PAD, y), line, font_body, emoji_body, '#5D5D5D')
        y += line_h_body

    return img


def journal_image_bytes(journal, upload_folder):
    """返回手账长图的 PNG 字节流。"""
    img = render_journal_image(journal, upload_folder)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def journal_pdf_bytes(journal, upload_folder):
    """返回手账的 PDF 字节流（将长图封装为单页 PDF）。"""
    img = render_journal_image(journal, upload_folder)
    buf = io.BytesIO()
    img.save(buf, format='PDF', resolution=96)
    buf.seek(0)
    return buf

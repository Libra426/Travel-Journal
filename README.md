# 时光手账 · Travel Journal

基于 Flask 的智能旅行手账应用。上传旅行照片后，自动提取拍摄信息（GPS 经纬度、拍摄时间、相机型号），结合百度地图逆地理编码与视觉大模型图片分析，自动生成小红书风格的游记，并以地图足迹、日历、标签等方式管理，支持导出 PNG 长图 / PDF。

## 功能特性

- **用户系统**：注册 / 登录 / 退出，密码使用 Werkzeug 哈希存储，手账按用户私有隔离。
- **多图上传**：最多 9 张、总大小 40MB 以内，支持点击或拖拽，兼容单图 `file` 与多图 `files` 字段。
- **EXIF 提取**：解析 GPS 经纬度（含坐标范围校验）、拍摄时间、相机型号，自动处理 IFDRational 序列化问题。
- **地理位置识别**：多张带 GPS 照片做「省·市众数投票」，百度逆地理编码（WGS84→BD09 转换），高德作备用。
- **视觉分析**：Qwen2.5-VL 视觉大模型逐张分析图片（地标、文字、景观、天气线索）。
- **游记生成**：DeepSeek 文本大模型整合时间、地点、天气、心情、同行人、附近景点与自定义提示词，生成小红书风格游记。
- **手账管理**：增删改查 + 搜索过滤（关键词 / 地点 / 心情 / 标签 / 月份）。
- **可视化**：中国地图足迹点亮（省份 + 城市）、日历视图、图片主色调卡片。
- **导出**：导出 PNG 长图或 PDF（Pillow 渲染，支持中文与 emoji 混排）。

## 技术栈

- 后端：Python 3、Flask 3.1.3、Werkzeug
- 数据库：SQLite（`app.db`）
- 图像处理：Pillow 11.3.0
- HTTP：requests 2.33.1
- 第三方服务：百度地图（逆地理编码 / 周边景点）、DeepSeek（文本生成）、通义千问 Qwen-VL（视觉分析）

## 目录结构

```
Travel-Journal/
├── app.py                 # Flask 主应用与路由
├── requirements.txt       # 依赖清单
├── app.db                 # SQLite 数据库
├── journals.json          # 旧版 JSON 数据（仅首次启动迁移用）
├── templates/
│   ├── login.html         # 登录 / 注册页
│   └── index.html         # 主页（上传、地图、日历、列表）
├── static/
│   ├── uploads/           # 上传的图片
│   ├── china-map.svg      # 中国地图 SVG
│   ├── map.js             # 地图足迹逻辑
│   └── test_image.jpg     # 视觉测试用图
├── utils/
│   ├── database.py        # SQLite 数据访问层（用户 + 手账）
│   ├── exif_extractor.py  # EXIF 提取
│   ├── baidu_map.py       # 逆地理编码 / 周边景点
│   ├── vision_model.py    # 视觉大模型分析
│   ├── text_model.py      # 文本大模型游记生成
│   └── exporter.py        # PNG / PDF 导出
├── pic/                   # UML 图生成脚本与图片
└── tests/                 # 单元测试
```

## 安装与运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置密钥：复制 .env.example 为 .env，填入你的 API Key
# 3. 启动
python app.py
```

浏览器访问 http://127.0.0.1:5000 。

> 首次启动会自动创建数据库表；若存在旧版 `journals.json` 且用户表为空，会自动创建默认账号 `admin / 123456` 并导入旧数据。

## 环境变量配置

在项目根目录复制 `.env.example` 为 `.env`，填入你自己的 Key。`.env` 已被 `.gitignore` 忽略，不会被提交到 Git。

| 变量             | 说明                               |
| ---------------- | ---------------------------------- |
| `TEXT_API_KEY`   | 文本模型（DeepSeek）               |
| `VISION_API_KEY` | 视觉模型（通义千问 Qwen-VL）       |
| `BAIDU_API_KEY`  | 百度地图                           |
| `SECRET_KEY`     | Flask 会话密钥（可选，默认已内置） |

## 主要 API

| 方法   | 路径                          | 说明                 |
| ------ | ----------------------------- | -------------------- |
| POST   | `/api/register`               | 注册                 |
| POST   | `/api/login`                  | 登录                 |
| POST   | `/api/logout`                 | 退出登录             |
| GET    | `/api/me`                     | 当前登录状态         |
| GET    | `/journals`                   | 获取当前用户手账列表 |
| POST   | `/upload`                     | 上传图片并生成手账   |
| PUT    | `/journals/<id>`              | 修改手账             |
| DELETE | `/journals/<id>`              | 删除手账             |
| GET    | `/journals/<id>/export/image` | 导出 PNG 长图        |
| GET    | `/journals/<id>/export/pdf`   | 导出 PDF             |

## 测试

```bash
python -m unittest tests.test_geolocation
python -m unittest tests.test_vision
python -m unittest tests.test_text_generation
```

## 注意事项

- 图片导出依赖 Windows 中文字体（`msyh.ttc` 等）与 emoji 字体（`seguiemj.ttf`）。
- 上传上限 40MB、一次最多 9 张图片。
- 图片尽量使用带有 GPS 信息的图片，以提高位置识别准确性。
- 本项目为课程 / 学习项目，密钥请通过 `.env` 管理，勿提交到 Git。

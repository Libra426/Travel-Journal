import base64
import os

import requests

VISION_API_KEY = os.environ.get('VISION_API_KEY', '')
VISION_MODEL = 'qwen2.5-vl-72b'
VISION_URL = 'https://api.modelarts-maas.com/v1/chat/completions'


def encode_image(image_path):
    """
    将图片编码为base64
    """
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def analyze_image(image_path):
    """
    使用视觉大模型分析图片内容
    """
    base64_image = encode_image(image_path)
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {VISION_API_KEY}'
    }
    
    # 优化提示词，提高对图片中地址信息的检索准确度，避免幻觉
    prompt = """请详细分析这张图片，特别注意以下信息：
1. 明显的地标建筑或景点名称
2. 街道名称、路牌、标识等文字信息
3. 自然景观特征（如山脉、河流、海滩等）
4. 建筑物风格和特点
5. 环境特征（城市、乡村、海边、山区等）
6. 可能的地理位置线索
7. 图片中的季节和天气情况

请严格基于图片实际内容进行描述，不要添加任何图片中不存在的信息。
如果图片中没有某些信息，请明确说明"未在图片中看到"。

请以结构化的方式输出分析结果，包括：
- 图片整体描述
- 地理位置线索
- 可能的拍摄地点
- 图片中的关键元素"""
    
    # Qwen 2.5-VL-72B模型的请求格式
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.3  # 降低温度，减少幻觉
    }
    
    try:
        response = requests.post(VISION_URL, headers=headers, json=payload)
        data = response.json()
        if 'choices' in data:
            return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error in image analysis: {e}")
    return "无法分析图片内容"


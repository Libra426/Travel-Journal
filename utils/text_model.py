import os

import requests

TEXT_API_KEY = os.environ.get('TEXT_API_KEY', '')
TEXT_MODEL = 'deepseek-v4-pro'
TEXT_URL = 'https://api.deepseek.com/chat/completions'


def generate_travel_journal(image_analysis, location, datetime, nearby_attractions,
                            mood=None, companions=None, weather=None, custom_prompt=None):
    """
    使用文本大模型生成小红书风格的旅游手账
    支持整合用户补充的心情、同行人、天气、自定义提示词等个性化信息
    """
    # 构建提示词
    prompt = f"请根据以下信息，生成一篇小红书风格的旅游手账：\n\n"
    prompt += f"图片内容描述：{image_analysis}\n\n"
    if location:
        prompt += f"地理位置：{location}\n\n"
    if datetime:
        prompt += f"拍摄时间：{datetime}\n\n"
    if weather:
        prompt += f"天气情况：{weather}\n\n"
    if mood:
        prompt += f"当时心情：{mood}\n\n"
    if companions:
        prompt += f"同行人：{companions}\n\n"
    if nearby_attractions:
        prompt += "附近景点：\n"
        for attraction in nearby_attractions:
            prompt += f"- {attraction['name']}（距离：{attraction['distance']}米）\n"
        prompt += "\n"
    if custom_prompt:
        prompt += f"用户补充的个性化要求：{custom_prompt}\n\n"

    prompt += "要求：\n"
    prompt += "1. 语言风格类似小红书的游记，亲切自然，有个人感受\n"
    prompt += "2. 结构清晰，有开头、正文和结尾\n"
    prompt += "3. 适当的在每一段落中使用emoji增加趣味性\n"
    prompt += "4. 字数控制在800字左右\n"
    prompt += "5. 不要在文本中添加'标题'二字\n"
    prompt += "6. 不要使用**和*标记符号\n"
    prompt += "7. 标题使用一句话,控制在10个字左右,且具有吸引性和文采,突出景点的特点\n"
    prompt += "8. 正文使用段落,每个段落控制在100字左右\n"
    prompt += "9. 文章内容偏向游玩体验,不要显得太推荐性质\n"
    prompt += "10. 文章内容丰富一些,包含结合图片内容、地理位置和时间信息，提到附近的景点，给出一些旅游建议和旅游感受,营造身临其境的感觉\n"
    prompt += "11. 文章内容中不能出现推测性词语,要写的像真实去过一样\n"

    if mood or companions:
        prompt += "12. 在行文中自然融入用户的心情与同行人信息，例如提到与朋友/家人一起游玩、当时的情绪等，使其更真实个性化\n"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {TEXT_API_KEY}'
    }

    payload = {
        "model": TEXT_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
        "thinking": {"type": "disabled"}
    }

    try:
        response = requests.post(TEXT_URL, headers=headers, json=payload)
        data = response.json()
        if 'choices' in data:
            return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error in generating travel journal: {e}")
    return "无法生成旅游手账"

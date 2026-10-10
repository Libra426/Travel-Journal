import unittest
import os
from utils.vision_model import analyze_image

class TestVision(unittest.TestCase):
    def test_analyze_image(self):
        """测试视觉模型分析图片"""
        # 确保有测试图片
        test_image_path = 'static/test_image.jpg'
        
        # 如果测试图片不存在，创建一个简单的测试图片
        if not os.path.exists(test_image_path):
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            os.makedirs(os.path.dirname(test_image_path), exist_ok=True)
            img.save(test_image_path)
        
        result = analyze_image(test_image_path)
        # 避免在Windows终端中打印包含特殊字符的文本
        try:
            print(f"图片分析结果: {result}")
        except UnicodeEncodeError:
            print("图片分析成功（包含特殊字符，无法在终端显示）")
        self.assertIsNotNone(result)
        self.assertNotEqual(result, "无法分析图片内容")

if __name__ == '__main__':
    unittest.main()
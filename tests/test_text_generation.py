import unittest
from utils.text_model import generate_travel_journal

class TestTextGeneration(unittest.TestCase):
    def test_generate_travel_journal(self):
        """测试文本模型生成旅游手账"""
        # 模拟数据
        image_analysis = "这是一张在海滩上拍摄的照片，蓝天白云，海浪拍打着沙滩，远处有几艘帆船。"
        location = "海南省三亚市亚龙湾"
        datetime = "2024:05:01 14:30:00"
        nearby_attractions = [
            {'name': '亚龙湾热带天堂森林公园', 'distance': 500},
            {'name': '亚龙湾海底世界', 'distance': 300}
        ]
        
        result = generate_travel_journal(image_analysis, location, datetime, nearby_attractions)
        # 避免在Windows终端中打印包含emoji的文本
        try:
            print(f"旅游手账生成结果: {result}")
        except UnicodeEncodeError:
            print("旅游手账生成成功（包含emoji字符，无法在终端显示）")
        self.assertIsNotNone(result)
        self.assertNotEqual(result, "无法生成旅游手账")
        self.assertGreater(len(result), 100)

if __name__ == '__main__':
    unittest.main()
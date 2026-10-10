import unittest
from utils.baidu_map import reverse_geocode, get_nearby_attractions

class TestGeolocation(unittest.TestCase):
    def test_reverse_geocode(self):
        """测试地理位置逆解析"""
        # 使用一个已知的经纬度（北京天安门）
        latitude = 39.9042
        longitude = 116.4074
        
        result = reverse_geocode(latitude, longitude)
        print(f"逆解析结果: {result}")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn('address', result)
        self.assertIn('北京市', result['address'])
    
    def test_get_nearby_attractions(self):
        """测试获取附近景点"""
        # 使用一个已知的经纬度（北京天安门）
        latitude = 39.9042
        longitude = 116.4074
        
        attractions = get_nearby_attractions(latitude, longitude)
        print(f"附近景点: {attractions}")
        self.assertIsInstance(attractions, list)
        self.assertGreater(len(attractions), 0)

if __name__ == '__main__':
    unittest.main()
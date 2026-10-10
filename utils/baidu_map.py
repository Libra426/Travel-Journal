import os

import requests
import math

BAIDU_API_KEY = os.environ.get('BAIDU_API_KEY', '')

# 坐标转换：WGS84转BD09
def wgs84_to_bd09(lat, lon):
    """
    将WGS84坐标系转换为百度BD09坐标系
    """
    x_pi = math.pi * 3000.0 / 180.0
    x = lon
    y = lat
    z = math.sqrt(x * x + y * y) + 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) + 0.000003 * math.cos(x * x_pi)
    bd_lon = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return bd_lat, bd_lon

def reverse_geocode(latitude, longitude):
    """
    利用百度地图API进行逆地理编码
    """
    # 转换坐标到百度坐标系
    bd_lat, bd_lon = wgs84_to_bd09(latitude, longitude)
    
    # 使用extensions=all获取详细信息
    url = f"https://api.map.baidu.com/reverse_geocoding/v3/?ak={BAIDU_API_KEY}&output=json&location={bd_lat},{bd_lon}&extensions=all"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get('status') == 0:
            address = data['result']['formatted_address']
            # 提取详细地址组件
            address_components = data['result'].get('addressComponent', {})
            # 提取附近兴趣点
            pois = data['result'].get('pois', [])
            
            result = {
                'address': address,
                'details': address_components,
                'pois': pois[:5]  # 取前5个兴趣点
            }
            return result
    except Exception as e:
        print(f"Error in reverse geocoding: {e}")
    
    # 尝试使用备用服务（高德地图）
    return reverse_geocode_amap(latitude, longitude)

def reverse_geocode_amap(latitude, longitude):
    """
    利用高德地图API进行逆地理编码（备用）
    """
    # 注意：这里需要替换为真实的高德API key
    amap_api_key = 'your_amap_api_key'
    if not amap_api_key or amap_api_key == 'your_amap_api_key':
        return None
    
    url = f"https://restapi.amap.com/v3/geocode/regeo?key={amap_api_key}&location={longitude},{latitude}&extensions=base"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get('status') == '1':
            address = data['regeocode']['formatted_address']
            return {'address': address, 'details': {}, 'pois': []}
    except Exception as e:
        print(f"Error in reverse geocoding with Amap: {e}")
    return None

def get_nearby_attractions(latitude, longitude, radius=1000, page_size=5):
    """
    查询附近的旅游景点
    """
    # 转换坐标到百度坐标系
    bd_lat, bd_lon = wgs84_to_bd09(latitude, longitude)
    
    url = f"https://api.map.baidu.com/place/v2/search?ak={BAIDU_API_KEY}&output=json&query=旅游景点&location={bd_lat},{bd_lon}&radius={radius}&page_size={page_size}&scope=2"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get('status') == 0:
            attractions = []
            for item in data['results']:
                attractions.append({
                    'name': item.get('name'),
                    'address': item.get('address'),
                    'distance': item.get('distance'),
                    'detail_url': item.get('detail_url')
                })
            return attractions
    except Exception as e:
        print(f"Error in getting nearby attractions: {e}")
    return []
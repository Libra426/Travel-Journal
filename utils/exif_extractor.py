from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os

# 坐标范围验证
def validate_coordinates(lat, lon):
    return -90 <= lat <= 90 and -180 <= lon <= 180

def get_if_exist(data, key):
    if key in data:
        return data[key]
    return None

def convert_to_degrees(value):
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def extract_exif(image_path):
    exif_data = {}
    try:
        image = Image.open(image_path)
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded == 'GPSInfo':
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]
                    # 注意：不保存原始 GPSInfo 字典——其中 GPSVersionID 是 bytes、
                    # 经纬度是 IFDRational，会导致后续 json.dumps 失败（500）。
                    # 下游只用解析后的 latitude / longitude 浮点数。

                    # 提取经纬度
                    if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
                        lat = convert_to_degrees(gps_data['GPSLatitude'])
                        if gps_data['GPSLatitudeRef'] != 'N':
                            lat = -lat
                        # 验证坐标范围
                        if validate_coordinates(lat, 0):
                            exif_data['latitude'] = lat
                    
                    if 'GPSLongitude' in gps_data and 'GPSLongitudeRef' in gps_data:
                        lon = convert_to_degrees(gps_data['GPSLongitude'])
                        if gps_data['GPSLongitudeRef'] != 'E':
                            lon = -lon
                        # 验证坐标范围
                        if validate_coordinates(0, lon):
                            exif_data['longitude'] = lon
                    
                    # 提取GPS精度信息（转 float，避免 IFDRational 无法 JSON 序列化）
                    if 'GPSDOP' in gps_data:
                        try:
                            exif_data['gps_accuracy'] = float(gps_data['GPSDOP'])
                        except (TypeError, ValueError):
                            exif_data['gps_accuracy'] = None
                elif decoded == 'DateTime':
                    exif_data['datetime'] = value
                # 提取相机信息，可能有助于判断拍摄地点
                elif decoded in ['Make', 'Model']:
                    exif_data[decoded] = value
    except Exception as e:
        print(f"Error extracting EXIF: {e}")
    return exif_data
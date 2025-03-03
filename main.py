import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
import webbrowser
import threading

# 和风天气API配置
API_KEY = "your api key"  # 替换为你的实际 API Key
BASE_URL = "https://devapi.qweather.com/v7/weather/3d"  # 3天天气预报接口地址
CITY_LOOKUP_URL = "https://geoapi.qweather.com/v2/city/lookup"  # 地理信息服务接口地址

app = Flask(__name__)

def search_city(city_name):
    """
    查询支持的城市名称或 ID
    :param city_name: 城市名称
    :return: 城市 ID 或 None
    """
    params = {
        "location": city_name,
        "key": API_KEY,
        "lang": "zh"  # 指定语言为中文
    }
    response = requests.get(CITY_LOOKUP_URL, params=params)
    data = response.json()
    
    if "code" in data and data["code"] == "200":
        if len(data["location"]) > 0:
            city_id = data["location"][0]["id"]
            return city_id
    return None

def get_weather(city_name, city_id):
    """
    查询指定城市的明天天气预报
    :param city_name: 城市名称（汉字）
    :param city_id: 城市 ID
    :return: 明天的天气信息或错误提示
    """
    try:
        params = {
            "location": city_id,
            "key": API_KEY,
            "lang": "zh"  # 指定语言为中文
        }
        
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        
        if "code" in data:
            if data["code"] == "200":
                # 获取明天的天气数据（索引为1）
                tomorrow_weather = data["daily"][1]
                result = (
                    f"城市: {city_name}\n"  # 使用城市名称而不是城市 ID
                    f"日期: {tomorrow_weather['fxDate']}\n"
                    f"天气: {tomorrow_weather['textDay']}\n"
                    f"最高温度: {tomorrow_weather['tempMax']}°C\n"
                    f"最低温度: {tomorrow_weather['tempMin']}°C\n"
                    f"湿度: {tomorrow_weather['humidity']}%\n"
                    f"风速: {tomorrow_weather['windSpeedDay']} km/h"
                )
                return result
            else:
                return f"查询失败，错误信息: {data['message']}"
        else:
            return f"API 返回的数据格式异常，缺少 'code' 字段。"
    
    except Exception as e:
        return f"发生错误: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_weather', methods=['POST'])
def api_get_weather():
    data = request.get_json()
    city_name = data.get('city_name')
    
    if not city_name:
        return jsonify({'error': '请输入城市名称'}), 400
    
    city_id = search_city(city_name)
    if city_id:
        weather_result = get_weather(city_name, city_id)
        return jsonify({'result': weather_result})
    else:
        return jsonify({'error': '无法找到对应的城市，请检查输入的城市名称。'}), 404

def open_browser():
    """自动打开浏览器访问应用"""
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == "__main__":
    # 在新线程中打开浏览器
    threading.Timer(1.0, open_browser).start()
    # 启动 Flask 应用
    app.run(debug=True)
import datetime
import random
import json


from baidusearch.baidusearch import search
from mcp.server import FastMCP

# 初始化MCP服务器
mcp = FastMCP('Search_manager')

@mcp.tool()
async def get_current_weather(city: str) -> str :
    """
    获取指定城市的天气情况

    Args:
        city: 指定的城市

    Returns:
        格式化的天气信息,例如:"北京今天时晴天"
    """
    weather_condition = ["晴天", "多云", "雨天"]
    random_weather = random.choice(weather_condition)

    return f"{city}今天是{random_weather}"

@mcp.tool()
async def baidu_search(query: str, num_results: int = 3) -> str:
    """
    调用搜索引擎搜索指定内容

    Args:
        query: 要查询的内容或者关键词
        num_results: 要查询的次数

    Returns:
        查询结果
    """
    results = search(query, num_results=num_results)
    # 转换为json
    results = json.dumps(results, ensure_ascii=False)
    return results

#查询当前时间的工具。返回结果示例:"当前时间：2025-10-20 12:12:19"
@mcp.tool()
async def get_current_time() -> str:
    """
    查询当前时间

    Returns:
        格式化的时间，例如:"当前时间:2024-10-12 12:21:10"
    """
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')

    return f"当前时间:{formatted_time}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
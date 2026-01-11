import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StdioServerParameters,
    StdioConnectionParams, MCPToolset,
)

model=LiteLlm(
                model="deepseek/deepseek-chat",
                api_key=os.environ.get('DEEPSEEK_API_KEY'),
                base_url="https://api.deepseek.com"
            )

SYSTEM_PROMPT="""
# 你是一个搜索智能体，你具有使用搜索引擎的工具，你现在在一个多智能体系统中，用户不会直接给你输入，你只会被规划智能体调用，所以当你被调用时，你要接收规划
智能体的输入，并且调用搜索相关的工具，进行搜索的相关操作
    
    ##你有一下工具组件：
    - Search_manager: 这个组件有一下工具函数：
        1. 查询指定城市的天气(需要传递城市名称)
        2. 查询当前时间(不需要传递参数)
        3. 调用搜索引擎搜索某个内容或者关键词(需要传递查询的内容或关键字,以及查询的次数,查询次数不应该大于5此)

    ## 如果你要调用查询工具，你可以估计查询的难度动态调整查询次数，但一般在3次，不可以超过5次。
    
    ## 注意你要回应的不是用户，而是规划智能体，如果规划智能体调用你时，你必须调用合适的工具。并且告诉它最后的执行结果。
"""

def create_search_agent() -> LlmAgent:
    """构建ADK智能体"""
    toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command='python',
                args=[r"C:\study\agent_communication\Projects\myA2AProjects\03_multiagents_demo\MCPserver\search_MCPserver.py"],
            ),
        ),
    )
    return LlmAgent(
        model=model,
        name='search_agent',
        description='一个可以借助搜索引擎搜索相关信息的智能体',
        instruction=SYSTEM_PROMPT,
        tools=[toolset],
    )
import os

from collections.abc import AsyncIterable
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents.structured_output import ToolStrategy
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from langchain_core.messages import AIMessage, ToolMessage
from typing import Literal, Any
from langchain_openai import ChatOpenAI
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver

# 2.2 配置MCP客户端
client = MultiServerMCPClient(
    {
        "File_manager": {
            "transport": "streamable_http",
            "url": "http://localhost:8000/mcp"
        },
    }
)

class ResponseFormat(BaseModel):
    """规定返回给用户信息的格式"""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str

class FileAgent:
    system_prompt = """
    # 你是一个文件智能体,你具有对文件进行增删改查的功能。你现在在一个多智能体的系统中，用户不会直接给你输入，你只会被规划智能体调用，所以当你被调用时，你要接收规划智能体的输入，
    并且通过调用操作文件相关的工具，进行文件的相关操作。
    
    # 你的工具自带文件夹的路径，所以你只需要接收一个文件的名称就可以了,比如你可能会接收到如'创建一个叫text1.txt的文件，里面写上123'的命令，
    你只需要传递比如test.txt这个字符串，如果要添加文件内容时也记得传递文件内容参数。
    
    ##你有一下工具组件：
    - File_manager: 这个组件有一下工具函数：
        1. 添加指定文件(需要传递文件名和内容(可选))
        2. 删除指定文件(需要传递文件名)
        3. 修改指定文件(需要传递文件名和修改内容，以及修改模式(True代表追加模式,False代表覆盖模式))
        4. 查询指定文件内容(需要传递文件名)
        5. 查询这个文件夹目前有的文件(不需要传递参数)

    ## 注意你要回应的不是用户，而是规划智能体，如果规划智能体调用你时，你必须调用合适的工具。并且告诉它最后的执行结果。
    """

    format_instruction = """
        如果你需要规划智能体提供更多的信息来完成请求，设置status为"input_required"
        如果在处理请求的时候出现了错误，设置status为"error"
        如果你完成了规划智能体的请求，设置status为"input_required"
    """

    # 1.配置智能体
    def __init__(self):
        llm = ChatOpenAI(
            model='deepseek-chat',
            temperature=0.8,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
        )

        # 获取MCP工具
        import asyncio
        loop = asyncio.new_event_loop()
        tools = loop.run_until_complete(client.get_tools())
        loop.close()

        self.agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=self.system_prompt,
            middleware=[SummarizationMiddleware(
                model=llm,
                max_tokens_before_summary=4000,  # Trigger summarization at 4000 tokens
                messages_to_keep=20,  # Keep last 20 messages after summary
            )],
            checkpointer=InMemorySaver(),
            response_format=ToolStrategy(ResponseFormat)
        )

    # 2. 定义信息处理方法
    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        config : RunnableConfig = {'configurable' : {"thread_id" : context_id}}
        # 2.1 异步流式调用
        async for chunk in self.agent.astream(
                input={"messages": [{"role": "user", "content": query}]},
                config=config,
                stream_mode="values",
        ):
            message = chunk['messages'][-1]
            # agent尝试调用工具
            if isinstance(message, AIMessage) and message.tool_calls and len(message.tool_calls)>0 :
                yield{
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '正在准备工作...'
                }
            # tool正在执行
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '正在工作中...'
                }
        yield self.get_agent_response(config)


    # 再扩展定义agent回应的内容
    def get_agent_response(self, config):
        current_state = self.agent.get_state(config)   ######### 得到当前的状态: status: Literal['input_required', 'completed', 'error']  ########
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(structured_response, ResponseFormat):
            # 需要user的额外输入
            if structured_response.status == 'input_required':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            # 出现错误
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            # 任务完成
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }
        # 出现问题
        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                '无法处理，请稍后再试'
            ),
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
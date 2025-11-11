import base64
import os

from collections.abc import AsyncIterable
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from langchain_core.messages import AIMessage, ToolMessage
from typing import Literal, Any
from langchain_openai import ChatOpenAI
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver

@tool
def encode(s: str)->str:
    """可以将某个字符串进行加密"""
    key = os.getenv('KEY')
    temp_result = ""
    for i, char in enumerate(s):
        if char.isalpha():
            ascii_offset = 65 if char.isupper() else 97
            shift = ord(key[i % len(key)]) % 26
            temp_result += chr((ord(char)-ascii_offset-shift)%26 + ascii_offset)
        else:
            temp_result += char

    result = ""
    for i, char in enumerate(temp_result):
        key_char = key[i%len(key)]
        result += chr(ord(char)^ord(key_char))

    return base64.b64encode(result.encode('latin-1')).decode('utf-8')

@tool
def decode(ciphertext: str):
    """ 可以将加密后的字符串解密 """
    key = os.getenv('KEY')

    s1 = base64.b64decode(ciphertext)

    temp_result = ""
    for i, char in enumerate(s1):
        key_char = key[i % len(key)]
        decrypted_char = chr(char ^ ord(key_char))
        temp_result += decrypted_char

    result = ""
    for i, char in enumerate(temp_result):
        if char.isalpha():
            ascii_offset = 65 if char.isupper() else 97
            shift = ord(key[i % len(key)]) % 26
            decrypted_char = chr((ord(char) - ascii_offset + shift) % 26 + ascii_offset)
            result += decrypted_char
        else:
            result += char

    return result

class ResponseFormat(BaseModel):
    """规定返回给用户信息的格式"""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str

class CleverCatAgent:

    system_prompt = """
    你是一个聪明的CatAgent,你的功能就是使用'decode'工具对用户提供的一串加密的字符串进行解密，
    或者使用'encode'工具对用户提供的一串字符串进行解密
    如果用户询问你与解密某个密文的事情或者加密某个字符串的事情无关，请礼貌地回复说你无法帮助并且只能进行加密或者密文的解密，
    如果用户没有提供字符串或者密文或者字符串或者密文没有给完全，你将不确定最终的密文或者字符串是什么
    不要尝试回答不确定的问题或者使用工具用于其他目的
    """

    format_instruction = """
        如果你需要用户提供更多的信息来完成请求，设置status为"input_required"
        如果在处理请求的时候出现了错误，设置status为"error"
        如果你完成了用户的请求，设置status为"input_required"
    """

    # 1.配置智能体
    def __init__(self):
        llm = ChatOpenAI(
            model='deepseek-chat',
            temperature=0.8,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
        )
        self.agent = create_agent(
            model=llm,
            tools=[decode, encode],
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
        # 2.1 流式调用
        for chunk in self.agent.stream(
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
        print(f"current_state: {current_state}")
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
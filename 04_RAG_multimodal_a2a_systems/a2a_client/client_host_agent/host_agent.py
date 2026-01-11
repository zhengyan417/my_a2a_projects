import asyncio
import base64
import json
import os
import sys
import uuid

import httpx

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from a2a.client import A2ACardResolver, ClientConfig
from a2a.types import (
    DataPart,
    Part,
    Role,
    TextPart,
    TransportProtocol
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from remote_agent_connection import *
from timestamp_ext import TimestampExtension

load_dotenv() # 夹杂环境变量


class HostAgent:
    """这个智能体负责协调远程智能体"""

    def __init__( # 初始化
        self,
        remote_agent_addresses: list[str], # 远程智能体的URL
        http_client: httpx.AsyncClient, # httpx客户端
        task_callback: TaskUpdateCallback | None = None, # 任务更新回调
    ):
        self.task_callback = task_callback # 任务回调
        self.httpx_client = http_client # httpx客户端
        self.timestamp_extension = TimestampExtension() # 时间戳扩展
        config = ClientConfig( # 创建客户端配置
            httpx_client=self.httpx_client, # httpx客户端
            supported_transports=[ # 支持的传输协议
                TransportProtocol.jsonrpc, # jsonrpc协议
                TransportProtocol.http_json, # http_json协议
            ],
        )
        client_factory = ClientFactory(config) # 创建客户端工厂
        client_factory = self.timestamp_extension.wrap_client_factory( # 时间戳扩展
            client_factory
        )
        self.client_factory = client_factory # 客户端工厂
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {} # 远程智能体连接
        self.cards: dict[str, AgentCard] = {} # 智能体卡片
        self.agents: str = '' # 智能体名称
        loop = asyncio.get_running_loop() # 获取当前运行的loop
        loop.create_task( # 创建一个任务
             self.init_remote_agent_addresses(remote_agent_addresses) # 初始化远程智能体的地址
        )

    async def init_remote_agent_addresses( # 获取所有的远程的agent的信息
        self, remote_agent_addresses: list[str] # 所有远程智能体的地址
    ):
        async with asyncio.TaskGroup() as task_group: # 创建一个任务组
            for address in remote_agent_addresses: # 遍历每一个地址
                task_group.create_task(self.retrieve_card(address)) # 对每一个地址获取智能体卡片

    # 获取智能体卡片
    async def retrieve_card(self, address: str):
        card_resolver = A2ACardResolver(self.httpx_client, address) # 创建一个智能体卡片解析器
        card = await card_resolver.get_agent_card() # 解析智能体卡片
        self.register_agent_card(card) # 注册智能体卡片

    # 注册智能体卡片
    def register_agent_card(self, card: AgentCard): # 注册智能体卡片
        remote_connection = RemoteAgentConnections(self.client_factory, card) # 创建一个远程智能体连接
        self.remote_agent_connections[card.name] = remote_connection # 保存远程智能体连接
        self.cards[card.name] = card # 保存智能体卡片
        agent_info = [] # 初始化智能体信息列表
        for ra in self.list_remote_agents(): # 遍历所有远程智能体
            agent_info.append(json.dumps(ra)) # 转换为json字符串
        self.agents = '\n'.join(agent_info) # 拼接成字符串

    # 创建客户端智能体
    def create_agent(self) -> Agent:
        return Agent( # 创建智能体
            model=LiteLlm( # 创建LiteLlm模型
                model="dashscope/qwen-max", # 通义千问模型
                api_key=os.environ.get('DASHSCOPE_API_KEY'), # APIKEY
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1" # 模型地址
            ),
            name='A2A客户端智能体', # 模型名称
            instruction=self.root_instruction, # 系统提示词
            before_model_callback=self.before_model_callback, # 模型调用之前处理逻辑
            description="这个智能体负责将用户请求拆解为可由子智能体执行的任务", # 描述
            tools=[ # 工具列表
                self.list_remote_agents, # 列出远程智能体
                self.send_message, # 发送消息
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str: # 获取系统提示
        current_agent = self.check_state(context) # 获取当前智能体
        return f"""你是一位专业的任务分派专家，能够将用户请求委派给合适的远程智能体（Agent）。

发现能力：
- 你可以使用 `list_remote_agents` 工具来列出当前可用的远程智能体，以便选择合适的对象来处理任务。

执行操作：
- 对于需要执行具体操作的请求，你可以使用 `send_message` 工具与远程智能体交互，以完成相应动作。

在回复用户时，请务必注明所使用的远程智能体名称。

请始终依赖工具来处理用户请求，切勿自行编造答案。如果你不确定如何处理，请向用户询问更多细节。
请主要关注对话中最近的部分。

可用智能体：
{self.agents}

当前活跃智能体：{current_agent['active_agent']}
"""

    # 检查不同A2A server状态
    @staticmethod
    def check_state(context: ReadonlyContext):
        state = context.state # 获取当前状态
        if (
            'context_id' in state # 如果有context_id
            and 'session_active' in state # 如果有session_active
            and state['session_active'] # 如果session_active为True
            and 'agent' in state # 如果有agent
        ):
            return {'active_agent': f'{state["agent"]}'} # 返回当前激活的智能体
        return {'active_agent': 'None'} # 返回None

    @staticmethod
    def before_model_callback(callback_context: CallbackContext, llm_request): # 模型调用之前处理逻辑

        state = callback_context.state # 获取当前状态
        if 'session_active' not in state or not state['session_active']: # 如果当前会话状态没有激活
            state['session_active'] = True # 激活当前会话状态

    # 列出远程可以的使用的智能体的信息
    def list_remote_agents(self):
        """列出所有可以远程指派任务的智能体"""
        if not self.remote_agent_connections: # 如果没有远程智能体
            return [] # 返回空列表

        remote_agent_info = [] # 初始化远程智能体列表
        for card in self.cards.values(): # 遍历所有远程智能体
            remote_agent_info.append( # 添加远程智能体信息
                {'name': card.name, 'description': card.description} # 名字与描述
            )
        return remote_agent_info # 返回远程智能体列表

    # 发送信息
    async def send_message(
        self, agent_name: str, message: str, tool_context: ToolContext
    ):
        """向指定的远程智能体发送一个任务，支持流式传输（若该智能体支持）或非流式传输。"""

        state = tool_context.state # 获取当前状态
        state['agent'] = agent_name # 获取智能体名字
        client = self.remote_agent_connections[agent_name] # 获取远程智能体连接客户端

        task_id = None # 生成任务ID
        context_id = state.get('context_id', None) # 获取上下文ID
        message_id = str(uuid.uuid4()) # 生成消息ID

        # 2. 建立信息格式
        request_message = Message( # 创建消息
            role=Role.user, # 角色
            parts=[Part(root=TextPart(text=message))], # 内容
            message_id=message_id, # 消息ID
            context_id=context_id, # 上下文ID
            task_id=task_id, # 任务ID
        )

        # 添加用户上传的文件
        # for part in tool_context.message.parts:
        #     root = part.root
        #     if hasattr(root, 'inline_data') and root.inline_data is not None:
        #         inline_data = root.inline_data
        #         data = inline_data.data
        #         message.parts.append(
        #             Part(
        #                 root=FilePart(
        #                     file=FileWithBytes(name="upload_file", bytes=data)
        #                 )
        #             )
        #         )

        # 3. 发送信息
        response = await client.send_message(request_message) # 发送消息，获取回复

        # 4. 分析response
        # 4.1 message：转换格式后直接返回
        if isinstance(response, Message): # 如果是消息
            return await convert_parts(response.parts, tool_context) # 直接返回

        # 4.2 task: 判断task状态
        task: Task = response # 获取任务
        state['session_active'] = task.status.state not in [ # 当前会话是否仍然在进行中
            TaskState.completed,
            TaskState.canceled,
            TaskState.failed,
            TaskState.unknown,
        ]
        # 更新状态
        if task.context_id: # 如果有context_id
            state['context_id'] = task.context_id # 保存上下文 ID

        if task.status.state == TaskState.input_required: # 需要用户额外输入
            tool_context.actions.skip_summarization = True # 保留原始信息
            tool_context.actions.escalate = True # 交还控制权
        elif task.status.state == TaskState.canceled: # 如果任务取消
            return f"任务取消,请稍后再试" # 返回错误信息
        elif task.status.state == TaskState.failed: # 如果任务出错
            raise ValueError(f'{agent_name}任务({task.id})处理失败') # 抛出异常

        response = [] # 初始化回复列表
        if task.status.message: # 如果有任务信息
            if ts := self.timestamp_extension.get_timestamp( # 添加时间戳
                Message(parts=[Part(root=TextPart(text=task.status.message))], message_id=message_id,role=Role.agent)# 消息
            ):
                response.append(f'[at {ts.astimezone().isoformat()}]') # 添加包含时间戳的消息
            response.extend( # 添加任务信息
                await convert_parts(task.status.message.parts, tool_context) # 装换格式
            )
        if task.artifacts: # 如果有任务结果
            for artifact in task.artifacts: # 遍历所有结果
                if ts := self.timestamp_extension.get_timestamp(artifact): # 时间戳
                    response.append(f'[at {ts.astimezone().isoformat()}]') # 添加时间戳
                response.extend( # 添加结果
                    await convert_parts(artifact.parts, tool_context) # 装换格式
                )
        return response # 返回回复

# 转换格式工具函数
async def convert_parts(parts: list[Part], tool_context: ToolContext):
    res = [] # 初始化结果
    for p in parts: # 遍历所有部分
        res.append(await convert_part(p, tool_context)) # 转换每一个内容
    return res # 返回结果

async def convert_part(part: Part, tool_context: ToolContext): # 格式转换
    if part.root.kind == 'text': # 如果是文本
        return part.root.text # 返回文本
    if part.root.kind == 'data': # 如果是数据
        return part.root.data # 返回数据
    # 处理文件
    if part.root.kind == 'file': # 如果是文件
        file_id = part.root.file.name # 获取文件ID
        file_bytes = base64.b64decode(part.root.file.bytes) # 获取文件内容
        file_part = types.Part( # 创建文件内容
            inline_data=types.Blob( # 创建文件内容
                mime_type=part.root.file.mime_type, data=file_bytes
            )
        )
        await tool_context.save_artifact(file_id, file_part) # 保存文件
        tool_context.actions.skip_summarization = True # 跳过总结
        tool_context.actions.escalate = True # 升级
        return DataPart(data={'artifact-file-id': file_id}) # 返回文件ID
    return f'Unknown type: {part.kind}' # 返回未知类型
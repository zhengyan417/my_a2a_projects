import base64
import os

from typing import Any

from llama_index.core.output_parsers import PydanticOutputParser

from llama_cloud_services.parse import LlamaParse
from llama_index.core.llms import ChatMessage
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from llama_index.llms.dashscope import DashScope, DashScopeGenerationModels
from pydantic import BaseModel, Field


# 打印事件
class LogEvent(Event):
    msg: str # 消息

# 输入的event
class InputEvent(StartEvent):
    msg: str # 消息
    attachment: str | None = None # 文件内容
    file_name: str | None = None # 文件名

# 解析的 event
class ParseEvent(Event):
    attachment: str # 文件内容
    file_name: str # 文件名
    msg: str # 消息

# 聊天 Event
class ChatEvent(Event):
    msg: str # 消息

# 输出的 event
class ChatResponseEvent(StopEvent):
    response: str # 回复
    citations: dict[int, list[str]] # 引用


## 结构化输出
# 引用
class Citation(BaseModel):
    """文件里面特定行的引用内容"""

    # 引用编号
    citation_number: int = Field(
        description='生成回答时出现的引用编号'
    )
    # 引用的行数
    line_numbers: list[int] = Field(
        description='文件里面被引用的内容所在的行数'
    )

# 聊天回复
class ChatResponse(BaseModel):
    """对用户最终的回复内容"""
    # 回复信息
    response: str = Field(
        description='对用户的最终回复'
    )
    # 引用
    citations: list[Citation] = Field(
        default=list,
        description='包含了多个引用的列表,每一个引用都是行数,可以直接映射到对应的内容',
    )

# 工作流
class ParseAndChat(Workflow):
    def __init__( # 初始化
        self,
        timeout: float | None = None, # 超时时间
        verbose: bool = False, # 是否打印日志
        **workflow_kwargs: Any, # 其他参数
    ):
        super().__init__(timeout=timeout, verbose=verbose, **workflow_kwargs) # 父类初始化
        self._llm = DashScope(
            model_name=DashScopeGenerationModels.QWEN_MAX,
            api_key=os.getenv('DASHSCOPE_API_KEY'),
        ) # 大语言模型
        self._parser = LlamaParse(api_key=os.getenv('LLAMA_CLOUD_API_KEY')) # 文档解析器
        self._system_prompt_template = """ 
你是一个乐于助人的助手，能够回答关于文档的问题、提供引用，并进行对话。

以下是带行号的文档内容：  
  
{document_text}  

在引用文档内容时，请遵守以下规则：

1. 你的行内引用编号必须从 [1] 开始，并在每次新增引用时依次递增（即下一个引用为 [2]，再下一个是 [3]，依此类推）。
2. 每个引用编号必须对应文档中的具体行号。
3. 如果某处引用覆盖了连续的多行内容，请尽量使用一个引用编号来涵盖所有相关行。
4. 如果某处引用需要覆盖不连续的多行，可以使用类似 [2, 3, 4] 的格式（表示该引用对应第 2、3、4 行）。
5. 例如：如果回答中包含 “Transformer 架构……[1]。” 和 “注意力机制……[2]。”，且这两句话分别来自文档的第 10–12 行和第 45–46 行，那么对应的引用应为：citations = [[10, 11, 12], [45, 46]]。
6. 务必从 [1] 开始编号，并按顺序递增。绝对不要直接用行号作为引用编号（例如不要写成 [10] 来表示第 10 行），否则我会丢掉工作。

请严格按照以下 JSON 格式回答，不要包含任何其他内容：
{{
  "response": "你的回答文本",
  "citations": [
    {{
      "citation_number": 1,
      "line_numbers": [10, 11, 12]
    }},
    ...
  ]
}}
""" # 系统提示词

    @step # 路由
    def route(self, ev: InputEvent) -> ParseEvent | ChatEvent:
        if ev.attachment: # 如果有文件
            return ParseEvent(
                attachment=ev.attachment, file_name=ev.file_name, msg=ev.msg
            ) # 返回解析事件
        return ChatEvent(msg=ev.msg) # 返回聊天事件

    @step # 解析
    async def parse(self, ctx: Context, ev: ParseEvent) -> ChatEvent:
        ctx.write_event_to_stream(LogEvent(msg='Parsing document...')) # 推送事件
        results = await self._parser.aparse(
            base64.b64decode(ev.attachment),
            extra_info={'file_name': ev.file_name},
        ) # 解析文件
        ctx.write_event_to_stream(LogEvent(msg='Document parsed successfully.')) # 推送事件

        documents = await results.aget_markdown_documents(split_by_page=False) # 转换成markdown文件

        document = documents[0] # 使用第一页文件就行(因为没有分页)

        document_text = '' # 文件内容
        for idx, line in enumerate(document.text.split('\n')): # 一行一行读取
            document_text += f"<line idx='{idx}'>{line}</line>\n" # 内容格式化

        await ctx.store.set('document_text', document_text) # 保存文件内容
        return ChatEvent(msg=ev.msg) # 返回聊天事件

    @step # 聊天
    async def chat(self, ctx: Context, event: ChatEvent) -> ChatResponseEvent:
        current_messages = await ctx.store.get('messages', default=[]) # 获取历史信息
        current_messages.append(ChatMessage(role='user', content=event.msg)) # 添加用户信息
        ctx.write_event_to_stream(LogEvent(msg=f'Chatting with {len(current_messages)} initial messages.')) # 推送事件

        document_text = await ctx.store.get('document_text', default='') # 获取文件内容

        if document_text: # 如果有文件内容
            ctx.write_event_to_stream(LogEvent(msg='Inserting system prompt...')) # 推送事件
            prompt = self._system_prompt_template.format(document_text=document_text) # 获取系统提示

            history = "\n".join(
                f"{msg.role.upper()}: {msg.content}"
                for msg in current_messages[:-1]
            ) # 获取对话历史
            if history: # 如果有对话历史
                prompt += f"\n\n对话历史:\n{history}" # 添加对话历史
            prompt += f"\n\nUSER: {event.msg}" # 添加用户提问
        else: # 如果没有文件内容
            prompt = f"USER: {event.msg}\n\n请直接回答。" # 获取用户提问

        response = await self._llm.acomplete(prompt) # 调用模型
        raw_output = response.text.strip() # 获取模型输出

        parser = PydanticOutputParser(ChatResponse)  # 创建解析器
        try:
            response_obj: ChatResponse = parser.parse(raw_output) # 解析结构化输出
        except ValueError as _: # 如果本来就没有文件内容
            response_obj = ChatResponse(response=raw_output) # 只返回消息即可

        current_messages.append(
            ChatMessage(role='assistant', content=response_obj.response)
        ) # 保存信息
        await ctx.store.set('messages', current_messages) # 保存信息

        citations = {} # 创建引用字典
        if document_text and response_obj.citations: # 如果有文件内容且有引用
            for citation in response_obj.citations: # 遍历引用
                line_numbers = citation.line_numbers # 获取行号
                texts = [] # 创建文本列表
                for line_number in line_numbers: # 遍历行号
                    start_tag = f"<line idx='{line_number}'>" # 获取起始标签
                    end_tag = f"<line idx='{line_number + 1}'>" # 获取结束标签
                    start_idx = document_text.find(start_tag) # 获取起始索引
                    if start_idx == -1: # 如果找不到起始标签
                        continue # 跳过
                    end_idx = document_text.find(end_tag, start_idx) # 获取结束索引
                    if end_idx == -1: # 如果找不到结束标签
                        # 找下一个 </line> 或结尾
                        end_idx = document_text.find("</line>", start_idx) # 获取结束索引
                        if end_idx != -1: # 如果找不到结束标签
                            end_idx += len("</line>") # 加上结束标签长度
                        else: # 否则
                            end_idx = len(document_text) # 设置结束索引为结尾
                    content = document_text[start_idx + len(start_tag):end_idx].replace('</line>', '').strip() # 获取内容
                    texts.append(content) # 添加内容
                citations[citation.citation_number] = texts # 添加引用的内容

        return ChatResponseEvent(
            response=response_obj.response,
            citations=citations
        ) # 返回结果


async def main():
    """Test script for the ParseAndChat agent."""
    agent = ParseAndChat()
    ctx = Context(agent)

    with open('attention.pdf', 'rb') as f:
        attachment = f.read()
        attachment = base64.b64encode(attachment).decode()

    handler = agent.run(
        start_event=InputEvent(
            msg='这篇文章讲了什么',
            attachment=attachment,
            file_name='test.pdf',
        ),
        ctx=ctx,
    )

    response: ChatResponseEvent = await handler

    print(response.response)
    for citation_number, citation_texts in response.citations.items():
        print(f'Citation {citation_number}: {citation_texts}')

    handler = agent.run(
        msg='我刚才问你的上一个问题,你是怎么回答的?',
        ctx=ctx,
    )
    response: ChatResponseEvent = await handler
    print(response.response)


if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv()

    import asyncio

    asyncio.run(main())

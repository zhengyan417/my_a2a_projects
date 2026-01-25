import os
import asyncio
from typing import Any

from llama_index.core.output_parsers import PydanticOutputParser

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

from RAG_query_engine import RAGQueryEngine

import dotenv
dotenv.load_dotenv()

# 打印事件
class LogEvent(Event):
    msg: str # 消息

# 输入的event
class InputEvent(StartEvent):
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
    """文档里面特定内容的引用内容"""

    # 引用编号
    citation_number: int = Field(
        description='生成回答时出现的引用编号'
    )
    # 引用的文本
    texts: list[str] = Field(
        description='文档里面被引用的内容'
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
        description='包含了多个引用的列表',
    )

# 工作流
class DoctorRAGWorkflow(Workflow):
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
        
        
        self._rag_engine = RAGQueryEngine(
            llm_model_path=os.getenv('LLM_MODEL_PATH'),
            embed_model_path=os.getenv('EMBED_PATH'),
            storage_dir=os.getenv('STORAGE_DIR'),
            streaming=False,
            similarity_top_k=3,
            with_rerank=False,
            with_mmr=True,
            mmr_threshold=0.5,
            with_query_transform=False,
        ) # RAG查询引擎
        
        self._system_prompt_template = """ 
你是一个专业的中医助手，能够基于提供的医学知识库内容回答用户的问题、提供引用，并进行对话。

以下是医学知识库的相关内容：  

{context_str}  

在引用文档内容时，请遵守以下规则：

1. 你的行内引用编号必须从 [1] 开始，并在每次新增引用时依次递增（即下一个引用为 [2]，再下一个是 [3]，依此类推）。
2. 每个引用编号必须对应知识库中的相关内容段落。
3. 如果某处引用覆盖了连续的多段内容，请尽量使用一个引用编号来涵盖所有相关段落。
4. 例如：如果回答中包含 "根据中医理论……[1]。" 和 "这种情况需要……[2]。"，且这两句话分别来自知识库的不同段落，那么对应的引用应为：citations = [["根据中医理论..."], ["这种情况需要..."]]。
5. 务必从 [1] 开始编号，并按顺序递增。绝对不要直接用段落内容作为引用编号，否则我会丢掉工作。

请严格按照以下 JSON 格式回答，不要包含任何其他内容：
{{
  "response": "你的回答文本",
  "citations": [
    {{
      "citation_number": 1,
      "texts": ["引用的文本内容"]
    }},
    ...
  ]
}}
""" # 系统提示词

    @step # 路由
    def route(self, ev: InputEvent) -> ChatEvent:
        return ChatEvent(msg=ev.msg) # 返回聊天事件

    @step # 聊天
    async def chat(self, ctx: Context, event: ChatEvent) -> ChatResponseEvent:
        ctx.write_event_to_stream(LogEvent(msg='正在查询医学知识库...')) # 推送事件
        
        # 使用RAG引擎查询
        # response_text = self._rag_engine.query(event.msg)
        contexts = self._rag_engine.query_with_contexts(event.msg)
        
        ctx.write_event_to_stream(LogEvent(msg='医学知识库查询完成')) # 推送事件

        if contexts: # 如果有上下文
            ctx.write_event_to_stream(LogEvent(msg='添加系统提示词...')) # 推送事件
            prompt = self._system_prompt_template.format(context_str="\n\n".join(contexts)) # 获取系统提示
            prompt += f"\n\nUSER: {event.msg}" # 添加用户提问
        else: # 如果没有上下文
            prompt = f"USER: {event.msg}\n\n请直接回答。" # 获取用户提问

        response = await self._llm.acomplete(prompt) # 调用模型
        raw_output = response.text.strip() # 获取模型输出

        parser = PydanticOutputParser(ChatResponse)  # 创建解析器
        try:
            response_obj: ChatResponse = parser.parse(raw_output) # 解析结构化输出
        except ValueError as _: # 如果解析失败
            response_obj = ChatResponse(response=raw_output) # 只返回消息即可

        citations = {} # 创建引用字典
        if contexts and response_obj.citations: # 如果有上下文且有引用
            for citation in response_obj.citations: # 遍历引用
                citations[citation.citation_number] = citation.texts # 添加引用的内容

        return ChatResponseEvent(
            response=response_obj.response,
            citations=citations
        ) # 返回结果


async def main():
    """测试医生RAG智能体"""
    agent = DoctorRAGWorkflow() # 获取医生RAG智能体
    ctx = Context(agent) # 创建上下文

    handler = agent.run( # 运行智能体
        start_event=InputEvent( # 创建输入事件
            msg='', # 输入
        ),
        ctx=ctx, # 上下文
    )

    response: ChatResponseEvent = await handler # 获取回复

    print(response.response) # 打印回复
    for citation_number, citation_texts in response.citations.items(): # 获取所有引用
        print(f'引用 {citation_number}: {citation_texts}') # 打印引用


if __name__ == '__main__':

    asyncio.run(main()) # 运行主函数
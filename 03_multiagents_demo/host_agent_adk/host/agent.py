import asyncio
import json
import os
import uuid
from typing import Any, AsyncIterable, List

import httpx
import nest_asyncio
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task, Role, Part, TextPart, Message,
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from .host_agent_tools import (
    read_text_file
)
from .remote_agent_connection import RemoteAgentConnections

load_dotenv()
nest_asyncio.apply()


class HostAgent:
    """The Host agent."""

    def __init__(
        self,
    ):
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._agent = self.create_agent()
        self._user_id = "host_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(client, address)
                try:
                    card = await card_resolver.get_agent_card()
                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                except httpx.ConnectError as e:
                    print(f"ERROR: Failed to get agent card from {address}: {e}")
                except Exception as e:
                    print(f"ERROR: Failed to initialize connection for {address}: {e}")

        agent_info = [
            json.dumps({"name": card.name, "description": card.description})
            for card in self.cards.values()
        ]
        print("agent_info:", agent_info)
        self.agents = "\n".join(agent_info) if agent_info else "No friends found"

    @classmethod
    async def create(
        cls,
        remote_agent_addresses: List[str],
    ):
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self) -> Agent:
        return Agent(
            model=LiteLlm(
                model="deepseek/deepseek-chat",
                api_key=os.environ.get('DEEPSEEK_API_KEY'),
                base_url="https://api.deepseek.com"
            ),
            name="host",
            instruction=self.root_instruction,
            description="Host Agent用于协调远程智能体的工作",
            tools=[
                self.send_message,
                read_text_file,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        return f"""
        **角色:** 你是一个Host Agent, 一个文件安全管理专家。你主要的功能是与远程的智能体协调以完成用户的有关文件安全管理的功能。 

        **核心指引:**
        - 你自己有read_text_file与send_message两个工具。
        - 第一个工具可以用来读取指定文件夹内某一个文件的名字，用户只需要提供给你一个基本的文件名,如'test.txt'，之后你便可以调用这个工具读取到这个文件里面的密文。
        它会返回给你文件是否查询成功，以及里面的密文是什么。
        - 如果当前任务你无法解决时，你可以通过'send_message'向远程智能体发送请求。file_agent可以创建文件与删除文件,clever_cat_agent可以加密或者解密某个文件的内容。
        - 当用户要求你创建或者删除某个文件时，你必须调用file_agent,并且告诉它是创建还是删除，文件名,如test1.txt,以及如果是创建文件，请告诉它文件里面要写什么内容。
        - 请注意，文件里面的所有内容都是加密后的密文，同时为了确保安全性，你让file_agent创建文件时，传输给它的内容也必须是加密后的内容。但是如果用户要求你返回某一个文件里面的内容，
        你必须把这个文件里面的内容解密，然后把明文完整地放回给用户。当你需要加密或者解密时，你必须调用clever_cat_agent，并且告诉它是加密还是解密，以及要加密的明文或者要解密的密文。
        - 用户可能会让你读取某个文件的内容，或者删除某一个文件，以及创建某一个文件并且写上一段内容。注意用户让你写的内容是明文，而那个文件实际储存的是密文。所以你必须将
        任务分解并且调用其他远程智能体帮你完成这个工作。

        <Available Agents>
        {self.agents}
        </Available Agents>
        """

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Streams the agent's response to a given query.
        """
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                yield {
                    "is_task_complete": True,
                    "content": response,
                }
            else:
                yield {
                    "is_task_complete": False,
                    "updates": "The host agent is thinking...",
                }

    async def send_message(self, agent_name: str, query : str, tool_context: ToolContext):
        """Sends a task to a remote friend agent."""
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {agent_name} not found")
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f"Client not available for {agent_name}")

        # Simplified task and context ID management
        state = tool_context.state
        task_id = state.get("task_id", None)
        context_id = state.get("context_id", str(uuid.uuid4()))
        message_id = str(uuid.uuid4())

        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": query}],
                "messageId": message_id,
                "taskId": task_id,
                "contextId": context_id,
            },
        }
        # request_message =  Message(
        #     role=Role.user,
        #     parts=[Part(root=TextPart(text=query))],
        #     message_id=message_id,
        #     context_id=context_id,
        #     task_id=task_id,
        # )
        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )
        send_response: SendMessageResponse = await client.send_message(message_request)
        print("send_response", send_response)

        if not isinstance(
            send_response.root, SendMessageSuccessResponse
        ) or not isinstance(send_response.root.result, Task):
            print("Received a non-success or non-task response. Cannot proceed.")
            return

        if send_response.context_id:
            state['context_id'] = send_response.context_id
        state['task_id'] = send_response.id
        response_content = send_response.root.model_dump_json(exclude_none=True)
        json_content = json.loads(response_content)

        resp = []
        if json_content.get("result", {}).get("artifacts"):
            for artifact in json_content["result"]["artifacts"]:
                if artifact.get("parts"):
                    resp.extend(artifact["parts"])
        return resp


def _get_initialized_host_agent_sync():
    """Synchronously creates and initializes the HostAgent."""

    async def _async_main():
        # Hardcoded URLs for the friend agents
        friend_agent_urls = [
            "http://localhost:10001",  # file Agent
            "http://localhost:10000",  # clever cat Agent
        ]

        print("initializing host agent")
        hosting_agent_instance = await HostAgent.create(
            remote_agent_addresses=friend_agent_urls
        )
        print("HostAgent initialized")
        return hosting_agent_instance.create_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print(
                f"Warning: Could not initialize HostAgent with asyncio.run(): {e}. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing HostAgent within an async function in your application."
            )
        else:
            raise


root_agent = _get_initialized_host_agent_sync()


import logging  # 打印日志

from typing import Any
from uuid import uuid4

import httpx  # 异步支持，发送http请求

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (AgentCard, MessageSendParams, SendMessageRequest, SendStreamingMessageRequest)
from a2a.utils.constants import (AGENT_CARD_WELL_KNOWN_PATH, EXTENDED_AGENT_CARD_PATH)

async def main() -> None:
    # 0.配置logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = 'http://localhost:7890'

    # 客户端
    async with httpx.AsyncClient() as httpx_client:
        # 1.初始化A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,  # 客户端
            base_url=base_url, # 地址
        )

        # 2.获取AgentCard
        final_agent_card: AgentCard | None = None

        try:
            # 2.1 获取初版的agentCard
            logger.info(f"尝试从{base_url}{AGENT_CARD_WELL_KNOWN_PATH}获取初版AgentCard")
            _public_card = (await resolver.get_agent_card())  # resolver获取AgentCard
            logger.info("成功获取AgentCard:")
            logger.info(_public_card.model_dump_json(indent=2, exclude_none=True))
            final_agent_card = _public_card  # 第一个获得的agentCard

            # 2.2 获取高级的agentCard
            if _public_card.supports_authenticated_extended_card:
                try:
                    logger.info(f"\n尝试从{base_url}{AGENT_CARD_WELL_KNOWN_PATH}获取扩展的AgentCard")
                    # 定义令牌
                    auth_headers_dict = {
                        'Authorization': "Bearer dummy-token-for-extended-card"
                    }
                    # 尝试获取高级AgentCard
                    _extend_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict}
                    )
                    logger.info("成功获取扩展版AgentCard:")
                    logger.info(
                        _extend_card.model_dump_json(
                            indent=2, exclude_none=True
                        )
                    )
                    final_agent_card = _extend_card # 第二个AgentCard
                except Exception as e_extended:
                    logger.warning(
                        f'无法获取扩展版agentCard:{e_extended},将使用公开的public card.',
                        exc_info=True,
                    )
            elif _public_card:
                logger.info("\n只有公共的Agent card.")
        except Exception as e:
            logger.error(
                f"获取AgentCard时出错:{e}",
                exc_info=True
            )
            raise RuntimeError(
                "无法获取AgentCard"
            ) from e

        # 3. 发送信息
        # 3.1 配置客户端
        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card
        )
        logger.info("客户端初始化完成")

        # 3.2 配置发送的内容
        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': '你好，Cat Agent!'}
                ],
                'messageId': uuid4().hex,
            },
        }
        requests = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**send_message_payload))

        # 3.3 连接并且获取回复
        response = await client.send_message(requests)
        print(response.model_dump(mode='json', exclude_none=True))

        # # 4.流式输出
        # stream_requests = SendStreamingMessageRequest(id=str(uuid4()), params=MessageSendParams(**send_message_payload))
        # stream_response = client.send_message_streaming(stream_requests)
        # async for chunk in stream_response:
        #     print(chunk.model_dump(mode='json', exclude_none=True))


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())

"""
{
'id': 'e35d993e-370c-4f0c-9798-47af1275dd43', 
'jsonrpc': '2.0', 
'result': {
    'kind': 'message', 
    'messageId': 'eebfb826-6524-406e-aa55-11da35edb773', 
    'parts': [{'kind': 'text', 'text': '喵喵喵'}], 
    'role': 'agent'
    }
}


"""
import json
import enum
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from astrbot.api.message_components import Reply
from astrbot.core.message.message_event_result import MessageEventResult


@register(
    "message_debug",
    "Sukafon",
    "一个简单的 debug 插件，你可以自由修改需要打印的信息",
    "1.0.0",
)
class MessageDebug(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    def _format_recursive_block(self, items, indent, open_char, close_char) -> str:
        """辅助函数"""
        if not items:
            return f"{open_char}{close_char}"
        space = "  " * indent
        inner_space = "  " * (indent + 2)
        inner_content = ",\n".join(f"{inner_space}{item}" for item in items)
        return f"{open_char}\n{inner_content}\n{space}{close_char}"

    def format_obj(self, obj, indent=0) -> str:
        match obj:
            case int() | float() | bool() | None:
                return str(obj)
            case str():
                return repr(obj)
            case dict():
                items = [
                    f"{self.format_obj(k, indent + 2)}: {self.format_obj(v, indent + 2)}"
                    for k, v in obj.items()
                ]
                return self._format_recursive_block(items, indent, "{", "}")
            case list():
                items = [self.format_obj(x, indent + 2) for x in obj]
                return self._format_recursive_block(items, indent, "[", "]")
            case tuple():
                items = [self.format_obj(x, indent + 2) for x in obj]
                return self._format_recursive_block(items, indent, "(", ")")
            case set():
                items = [self.format_obj(x, indent + 2) for x in obj]
                return self._format_recursive_block(items, indent, "{", "}")
            # 使用 case _ if guard: 来处理自定义对象
            case _ if hasattr(obj, "__dict__"):
                cls_name = obj.__class__.__name__
                items = [
                    f"{k}={self.format_obj(v, indent + 2)}"
                    for k, v in obj.__dict__.items()
                ]
                return self._format_recursive_block(items, indent, f"{cls_name}(", ")")
            case _:
                return repr(obj)

    # 更深层次的递归序列化，避免简单 vars() 导致子对象未展开或异步 to_dict 被忽略
    def deep_vars(self, obj):
        match obj:
            case list():
                return [self.deep_vars(o) for o in obj]
            case dict():
                return {k: self.deep_vars(v) for k, v in obj.items()}
            case enum.Enum():
                return repr(obj)
            case _ if hasattr(obj, "__dict__"):
                return {k: self.deep_vars(v) for k, v in obj.__dict__.items()}
            case _:
                return obj

    def _create_debug_response(
        self, event: AstrMessageEvent, chain_to_debug: list, title: str
    ) -> MessageEventResult | None:
        """
        辅助函数：根据给定的消息链创建用于调试的响应消息。
        它会格式化消息链、打印日志，并根据平台类型构建不同的消息格式。

        :param event: 当前的事件对象。
        :param chain_to_debug: 需要调试的消息链。
        :param title: 日志和转发消息的标题。
        :return: 构建好的 MessageChain 对象，可直接发送或 yield。
        """

        # 1. 格式化消息链为易读字符串
        pretty_str = self.format_obj(chain_to_debug)

        # 2. 打印日志
        if self.config.get("console_print", False):
            logger.info(f"\n{title}\n{pretty_str}")

        # 3. 根据平台构建响应消息
        # 对 QQ 平台使用合并转发
        if self.config.get("message_reply", False):
            if event.platform_meta.name == "aiocqhttp":
                from astrbot.api.message_components import Node, Nodes, Plain

                # 把对象转换成深序列化的字典
                chain_dict = self.deep_vars(chain_to_debug)
                # 把字典格式化成字符串
                chain_json = json.dumps(chain_dict, indent=4, ensure_ascii=False)
                # 构造转发消息
                nodes = [
                    Node(
                        uin=event.get_sender_id(),
                        name=event.get_sender_name(),
                        content=[Plain(title + " -> Prettier String")],
                    ),
                    Node(
                        uin=event.get_sender_id(),
                        name=event.get_sender_name(),
                        content=[Plain(pretty_str)],
                    ),
                    Node(
                        uin=event.get_sender_id(),
                        name=event.get_sender_name(),
                        content=[Plain(title + " -> JSON String")],
                    ),
                    Node(
                        uin=event.get_sender_id(),
                        name=event.get_sender_name(),
                        content=[Plain(chain_json)],
                    ),
                    Node(
                        uin=event.get_sender_id(),
                        name=event.get_sender_name(),
                        content=[
                            Plain(
                                "# event.message_obj.raw_message: Object -> Prettier String"
                            )
                        ],
                    ),
                    Node(
                        uin=event.get_sender_id(),
                        name=event.get_sender_name(),
                        content=[
                            Plain(
                                json.dumps(
                                    event.message_obj.raw_message,
                                    indent=4,
                                    ensure_ascii=False,
                                )
                            )
                        ],
                    ),
                ]
                return event.chain_result([Nodes(nodes)])
            else:
                # 4. 为其他平台提供降级方案，直接发送文本
                return event.plain_result(f"{title}\n{pretty_str}")

    @filter.command("debug")
    async def debug(self, event: AstrMessageEvent):
        """使用 /debug 指令。可直接发送，也支持直接引用回复。"""
        # 尝试查找消息中的 Reply 组件
        reply_component = next(
            (comp for comp in event.get_messages() if isinstance(comp, Reply)), None
        )

        # 分支 1: 如果是回复消息，直接处理被回复的内容
        if reply_component:
            title = "# Reply in event.get_messages(): List[BaseMessageComponent]"
            response_message = self._create_debug_response(
                event, reply_component.chain, title
            )
            yield response_message
            return

        # 分支 2: 如果不是回复消息，提示用户并等待下一条消息
        yield event.plain_result("请在 60 秒内发送一条消息~")

        @session_waiter(timeout=60, record_history_chains=False)
        async def waiter(controller: SessionController, new_event: AstrMessageEvent):
            title = "# event.get_messages(): List[BaseMessageComponent]"
            response_message = self._create_debug_response(
                new_event, new_event.get_messages(), title
            )
            if response_message:
                await new_event.send(response_message)
            controller.stop()

        try:
            await waiter(event)
        except TimeoutError as _:
            yield event.plain_result("超时了，操作已取消！")
        except Exception as e:
            logger.error(f"debug waiter failed: {e}", exc_info=True)
            yield event.plain_result("处理时发生了一个内部错误。")
        finally:
            event.stop_event()

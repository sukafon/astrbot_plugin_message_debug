# Message Debug 插件

一个用于在 AstrBot 中快速调试消息结构与内容的插件。适用于开发插件或排查消息处理逻辑时查看消息链内部结构。

## 功能
- 使用 /debug 指令打印或转发被调试消息的可读化结构。
- 支持：
  - 对回复消息（Reply 组件）直接解析被回复的消息链并返回字符串美化结果。
  - 非回复场景下等待用户在 60 秒内发送一条消息进行调试。
  - 对 QQ 平台自动使用合并转发；其他平台降级为纯文本输出。
- 将调试信息同时写入 AstrBot 日志（可选择是否开启）。

## 使用方法
1. 在聊天中发送 `/debug`：
   - 如果是回复某条消息：插件会解析并返回被回复消息的结构（并在 QQ 上以合并转发展示）。
   - 如果不是回复：插件会提示“请在 60 秒内发送一条消息~”，你发送的下一条消息会被解析并返回。
2. 超时处理：60 秒内未发送消息则返回超时提示。

## 输出示例
```text
# Reply in event.get_messages(): List[BaseMessageComponent] -> Prettier-String
[
    Image(
        type='Image',
        file='{DDC522C5-6E61-583D-BDAC-2E3121A46C20}.jpg',
        subType=0,
        url='https://gchat.qpic.cn/gchatpic_new/0/0-0-DDC522C56E61583DBDAC2E3121A46C20/0',
        cache=True,
        id=40000,
        c=2,
        path='',
        file_unique=''
    ),
    Plain(
        type='Plain',
        text='111111111',
        convert=True
    )
]
```


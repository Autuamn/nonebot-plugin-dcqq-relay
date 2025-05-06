# QQ群-Discord 互通

![python](https://img.shields.io/badge/python-3.9+-blue?logo=python&logoColor=edb641 "python")

## 前言

OneBot 实现众多，表现各有不同，我的测试环境为 [Lagrange.Onebot](https://github.com/LagrangeDev/Lagrange.Core)，遇到 bug 请[提 issues](https://github.com/Autuamn/nonebot-plugin-dcqq-relay/issues/new)，务必附上日志

本人 python 水平有限，遇到你认为可以改进的方法和函数，或有任何不妥之处，或需要注释支持，也请提出

## 功能

可以在指定的QQ群和 Discord 频道之间同步消息，只支持普通的文字频道，不支持帖子频道

### 消息支持情况

❗✔️🟢🟡⚠️❌🔴

|类型 | QQ to Discord | Discord to QQ | 备注 |
|  -  | :-: | :-: | - |
|文字 | 🟢 | 🟢 | 🟢支持      |
|图片 | 🟢 | 🟢 | 🟡压缩为文字|
|At   | 🟡 | 🟡 | ⚠️不良好    |
|回复 | 🟢 | 🟢 |
|撤回 | 🟢 | ⚠️ |
|表情 | 🟡 | 🟡 |
|贴纸 |     | 🟡 |
|文件 | 🟢 | 🟢 |
|视频 | 🟢 | 🟢 |
|语音 | 🟢 | 🟢 |
|Embed|     | ⚠️ |
|xml  | ⚠️ |     |
|json | ⚠️ |     |


## 安装

### 使用 nb-cli 安装

在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

```bash
nb plugin install nonebot-plugin-dcqq-relay
```

### 使用包管理器安装

建议使用 poetry

- 通过 poetry 添加到 NoneBot2 项目的 pyproject.toml

```bash
poetry add nonebot-plugin-dcqq-relay
```

- 也可以通过 pip 安装

```bash
pip install nonebot-plugin-dcqq-relay
```

### 安装开发中版本

```bash
pip install git+https://github.com/Autuamn/nonebot-plugin-dcqq-relay.git@main
```

## 配置

### 机器人权限

> [!IMPORTANT]
> 请在 Discord App 的 Bot 配置中打开 `Message Content Intent`：
  ![Privileged Gateway Intentsp 配置](https://img.kookapp.cn/assets/2025-05/06/rNvTKVl7dl1mo0hr.png)
  并在 discord adapter 的 bot 配置中添加 intent `"message_content": true`：
> ```dotenv
> DISCORD_BOTS='[{"token": "xxx",
>     "intent": {
>       "guild_messages": true,
>       "message_content": true   <<--- 像这样
>     },"application_commands": {"*": ["*"]}}]'
> ```


推荐权限：管理员

最低权限：
- QQ：
  - 管理员（不给撤回功能将不正常）
- Discord：
  - Manage Messages（不给无法撤回）
  - Mention Everyone（不给无法转发@全体成员）
  - Manage Webhooks（不给要提供 Webhook）


### dcqq_relay_channel_links

- 类型：`json`
- 默认值：`[]`
- 说明：链接对应的QQ群与 Discord 频道，目前只支持一对一链接

配置文件示例

```dotenv
dcqq_relay_channel_links='[
    {
        "qq_group_id": 123132,
        "dc_guild_id": 456456,
        "dc_channel_id": 789789,
        "webhook_id": 4444444,
        "webhook_token": "asdxxx"
    },
    {
        "qq_group_id": int                # QQ群号
        "dc_guild_id": int                # Discord 服务器 id
        "dc_channel_id": int              # Discord 频道 id
        "webhook_id": Optional[int]       # （可选的）Discord 对应频道的 Webhook ID
        "webhook_token": Optional[str]    # （可选的）Discord 对应频道的 Webhook Token
                                        # 不要把注释放在此处！！
    }
]'
```
> [!IMPORTANT]
> Webhook 的相关配置是可选的，不填插件会自动获取，但是要给机器人 Manage Webhooks 权限

关于 Webhook 是什么请看：[使用網絡鉤手（Webhooks）](https://support.discord.com/hc/zh-tw/articles/228383668-%E4%BD%BF%E7%94%A8%E7%B6%B2%E7%B5%A1%E9%89%A4%E6%89%8B-Webhooks)

得到 Webhook URL 后，可从 URL 中获取 `webhook_id` 和 `webhook_token`

Webhook URL 形如：
`https://discord.com/api/webhooks/{webhook_id}/{webhook_token}`

例如：

当 Webhook URL 为 `https://discord.com/api/webhooks/1243529342621978694/kq1Vc3NsN4d3SB0MAusB-xbY_e8xMChQmxypIFna0c1lwQS-uL85fqupK2jFfkYtUR1h` 时

`1243529342621978694` 就是 `webhook_id`

`kq1Vc3NsN4d3SB0MAusB-xbY_e8xMChQmxypIFna0c1lwQS-uL85fqupK2jFfkYtUR1h` 就是 `webhook_token`

### dcqq_relay_unmatch_beginning

- 类型：`list[str]`
- 默认值：`["/"]`
- 说明：指明不转发的消息开头

### dcqq_relay_only_to_me

- 类型：`bool`
- 默认值：`False`
- 说明：指明是否只转发 @机器人 的消息

## 特别感谢

- [nonebot2](https://github.com/nonebot/nonebot2)
- [Lagrange.Core](https://github.com/LagrangeDev/Lagrange.Core)
- [nonebot-plugin-alconna](https://github.com/nonebot/plugin-alconna)
- [Discord-QQ-Msg-Relay](https://github.com/OasisAkari/Discord-QQ-Msg-Relay)
- [koishi-plugin-dcqq-relay](https://github.com/koishijs/koishi-plugin-dcqq-relay)

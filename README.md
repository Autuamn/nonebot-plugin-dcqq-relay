# QQ群-Discord 互通
<img src="https://img.shields.io/badge/python-3.9+-blue?logo=python&logoColor=edb641" alt="python">


## 前言
OneBot 实现众多，表现各有不同，我的测试环境为 [Lagrange.Onebot](https://github.com/LagrangeDev/Lagrange.Core)，遇到 bug 请[提 issues](https://github.com/Autuamn/nonebot-plugin-dcqq-relay/issues/new)，务必附上日志

本人 python 水平有限，遇到你认为可以改进的方法和函数，或有任何不妥之处，或需要注释支持，也请提出

## 功能
可以在指定的QQ群和 Discord 频道之间同步消息，只支持普通的文字频道，不支持帖子频道

### 目前支持的消息：
- [x] 文字
- [x] 图片
- [x] 表情
- [x] 回复消息
- [x] 撤回消息

### 尚未支持的消息：
- [ ] 文件
- [ ] 语音
- [ ] 视频
- [ ] ARK 消息
- [ ] Embed 消息

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

## 配置
### dcqq_relay_channel_links
- 类型：`json`
- 默认值：`[]`
- 说明：链接对应的QQ群与 Discord 频道，目前只支持一对一链接

配置文件示例
```dotenv
dcqq_relay_channel_links='[
    {
        qq_group_id: 123132,
        dc_guild_id: 456456,
        dc_channel_id: 789789
    },
    {
        qq_group_id: int    # QQ群号
        dc_guild_id: int    # Discord 服务器 id
        dc_channel_id: int  # Discord 频道 id
                            # 不要把注释放在此处！！
    }
]'
```

### dcqq_relay_unmatch_beginning
- 类型：`list[str]`
- 默认值：`["/"]`
- 说明：指明不转发的消息开头

## 特别感谢
- [nonebot2](https://github.com/nonebot/nonebot2)
- [Lagrange.Core](https://github.com/LagrangeDev/Lagrange.Core)
- [Discord-QQ-Msg-Relay](https://github.com/OasisAkari/Discord-QQ-Msg-Relay)
- [koishi-plugin-dcqq-relay](https://github.com/koishijs/koishi-plugin-dcqq-relay)

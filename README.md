# QQ频道-Discord 互通
<a href="https://raw.githubusercontent.com/Autuamn/nonebot-plugin-dcqg-relay/master/LICENSE">
    <img src="https://img.shields.io/github/license/Autuamn/nonebot-plugin-dcqg-relay" alt="license">
</a>
<img src="https://img.shields.io/badge/python-3.9+-blue?logo=python&logoColor=edb641" alt="python">


## 前言
本项目为自用插件，如果有需求或想法请提出，我尽量满足

因用到了QQ官方的频道机器人接口，功能少，限制多，而且很多功能我也没法测试，就没有支持。之后可能会出一个基于 OneBot 适配器的版本（懒）

目前QQ机器人不能发 url，如果从 Discord 转来的消息里带有 url 的活是发不出来的，目前我没有想到解决办法。有想法请提出

## 功能
可以在指定的QQ子频道和 Discord 频道之间同步消息，只支持普通的文字频道，不支持帖子频道

### 目前支持的消息：
- [x] 文字
- [x] 图片
- [x] 表情

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
nb plugin install nonebot-plugin-dcqg-relay
```

### 使用包管理器安装
建议使用 poetry
- 通过 poetry 添加到 NoneBot2 项目的 pyproject.toml
```bash
poetry add nonebot-plugin-dcqg-relay
```
- 也可以通过 pip 安装
```bash
pip install nonebot-plugin-dcqg-relay
```

## 配置
> [!TIP]
> 需要注意的是，本项目的使用[本地数据存储](https://github.com/nonebot/plugin-localstore)存储数据。如需更改目录请在配置文件中加入
> ```dotenv
> localstore_cache_dir=""   # 缓存目录
> localstore_config_dir=""  # 配置目录
> localstore_data_dir=""    # 数据目录
> ```

### dcqg_relay_channel_links
- 类型：`json`
- 默认值：`[]`
- 说明：链接对应的QQ子频道与 Discord 频道，目前只支持一对一链接

配置文件示例
```dotenv
dcqg_relay_channel_links='[
    {
        qq_guild_id: "123132",
        dc_guild_id: 456456,
        qq_channel_id: "78789",
        dc_channel_id: 123123,
        webhook_id: 456456,
        webhook_token: "xxx"
    },
    {
        qq_guild_id: str    # QQ频道 id
        dc_guild_id: int    # Discord 服务器 id
        qq_channel_id: str  # QQ子频道 id
        dc_channel_id: int  # Discord 频道 id
        webhook_id: int     # WebHook id
        webhook_token: str  # WebHook token
                            # 请不要将注释放在此处！！
    }
]'
```

### dcqg_relay_unmatch_beginning
- 类型：`list[str]`
- 默认值：`["/"]`
- 说明：指明不转发的消息开头

## 命令
目前只有一条命令：
- /commit_db

用于保存数据库

## 特别感谢
- [nonebot2](https://github.com/nonebot/nonebot2)
- [Discord-QQ-Msg-Relay](https://github.com/OasisAkari/Discord-QQ-Msg-Relay)
- [koishi-plugin-dcqq-relay](https://github.com/koishijs/koishi-plugin-dcqq-relay)

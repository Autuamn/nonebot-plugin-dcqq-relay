from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column


class MsgID(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    dcid: Mapped[int]
    qqid: Mapped[int]

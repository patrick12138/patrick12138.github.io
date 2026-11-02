"""环境配置：vault 与 skills 安装目录。

默认值 = 手机工作站（/var/minis）；PC 在 tools/config.local.json 里覆盖
（该文件已 gitignore，不入库）。CI / PC 没有对应目录时各消费点自行跳过。
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "vault_root": "/var/minis/mounts/Patrick's_Obsidian",
    "skills_dst": "/var/minis/skills",
}


def load():
    cfg = dict(DEFAULTS)
    p = os.path.join(_HERE, "config.local.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg

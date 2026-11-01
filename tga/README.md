# TGA 年度游戏提名 · 玩过没

The Game Awards 2014–2025 十二届「年度游戏」全提名（68 席）的可持续勾选清单。

**在线使用**：https://patrick12138.github.io/tga-checklist/

## 能做什么

- 五个状态：✅ 通关 / ◐ 玩过没通 / ♡ 想加入待玩 / ✕ 不打算玩 / ⊘ 没得玩（平台限制）
- 平台徽章：PC / PS / Switch / Xbox，按 2026-11 实际情况标注
- 只有 PS、Switch 独占、没有 PC 版的 14 席默认标为「没得玩」（可手动改）
- 进度按「可玩 54 席」计算，每年单独统计 X/可玩数
- 标记存在浏览器 localStorage，刷新不丢；可一键复制结果成文本
- 手机 / PC 自适应（PC 端 2–3 列网格）

## 数据来源

- 提名与获奖：[GameMall TGA 历届档案](https://www.gamemall.org/zh/tga)（`fetch.py` 抓取 12 个年度页解析）
- 平台可玩性：人工按 2026-11 的发行情况核对（`gen.py` 里的 `PLATS` 表）

## 重建

```bash
python3 fetch.py   # 重新抓提名 -> data.json
python3 gen.py     # 合并平台信息 + template.html -> index.html
```

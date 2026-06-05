# isaac-repentance-eden-seed-decoder

适配 **The Binding of Isaac: Repentance v1.9.1.17**，逆向伊甸开局生成规则。输入种子可计算伊甸开局属性、口袋道具与宝藏池道具；支持按条件反推种子。

## 功能

- **查种子**：红心/魂心、六项属性、口袋（饰品/卡牌/胶囊）、开局被动/主动道具
- **反推**：前缀遍历（如 `T44` → `T440`、`T441`…）或 u32 范围扫描，可按属性/口袋/道具筛选
- **Web UI**：`eden-seed-decoder --web`，浏览器操作
- **内存提取**（Windows）：从运行中的游戏进程提取 `proc.json` / `trinket_pool.json`

## 安装

需要 **Python 3.10+**。

```bash
git clone https://github.com/KamiMisuzu/isaac-repentance-eden-seed-decoder.git
cd isaac-repentance-eden-seed-decoder

# 建议：创建并激活虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
# source .venv/bin/activate

# 先升级 pip / setuptools（旧版 pip 在 pip install -e . 时可能报错 No module named pip）
python -m pip install --upgrade pip setuptools wheel

# 基础功能（查种子、反推单线程）
pip install -e .

# 反推加速（推荐，需 numpy + numba）
pip install -e ".[fast]"
```

也可不安装，直接在仓库根目录运行：

```bash
python predict_eden.py --web
```

## 用法

### Web 界面

```bash
eden-seed-decoder --web
# 或
python predict_eden.py --web
```

默认地址：<http://127.0.0.1:8765>

首次使用道具/饰品相关功能时，请在 Web「数据」面板点击 **提取**（需游戏正在运行，Windows）。

### 命令行查种子

```bash
eden-seed-decoder "ABCD EFGH"
eden-seed-decoder "ABCD EFGH" --json
eden-seed-decoder "ABCD EFGH" --ach-159
```

### 命令行反推

```bash
# 前缀遍历
eden-seed-decoder --reverse --prefix T44 --max-results 20

# 范围扫描
eden-seed-decoder --reverse --start 0 --end ffffffff --red 2 --max-results 10
```

## 项目结构

```
predict_eden.py      # CLI 入口
tools/               # 种子编解码、RNG、预测、反推
web/                 # 静态页面与 HTTP API
data/profiles/       # 运行时提取的 proc / trinket 数据
itempools.xml        # 物品池参考数据
```

## 说明

- 种子格式：`XXXX XXXX`（9 字符，中间空格）
- 反推「前缀遍历」与「范围扫描」互斥：填前缀后自动枚举匹配子串，忽略起点/终点
- 反推界面「被动 / 主动」与查种子结果一致，请按查种子显示的值填写

## License

MIT

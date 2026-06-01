# Invoice Printing

一个本地运行的发票 / 报销单打印排版工具。适合把电子发票、行程单、火车票、住宿票据等整理到 A4 页面，并生成差旅费报销单首页。

项目默认在本机运行，文件和 OCR 处理都在本地完成，适合个人报销整理场景。

## 功能

- 按费用类型上传：飞机车船费、市区交通费、旅馆费、其他
- 支持拖拽上传图片或 PDF
- A4 打印排版：普通发票上下两张，火车票半页最多 6 张
- 市区交通费图片自动裁剪白边
- 独立打印页，支持 macOS / Windows 打印快捷键提示
- 差旅费报销单首页，可填写公司名、部门、姓名、事由 / 项目
- 报销单信息会保存在浏览器本地，下次打开自动恢复
- 本地 PaddleOCR 服务，支持图片和 PDF OCR
- 多语言 i18n：简体中文、繁体中文、English、日本語、한국어、Deutsch、Français、Español
- 提供 favicon / manifest，方便在面板工具中添加为本地应用

## 快速开始

### 方式一：Docker 部署

先确保已经安装 Docker Desktop。

```bash
git clone git@github.com:OneBigMoon/Invoice-Printing.git
cd Invoice-Printing
docker compose up --build -d
```

打开浏览器访问：

```text
http://127.0.0.1:4173/
```

OCR 服务地址：

```text
http://127.0.0.1:8765/ocr
```

首次启动 PaddleOCR 可能需要下载模型，时间会稍长。

### 方式二：本地 Python 运行

建议使用 Python 3.10。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m http.server 4173
```

另开一个终端启动 OCR：

```bash
source .venv/bin/activate
python ocr_server.py
```

然后访问：

```text
http://127.0.0.1:4173/
```

## 使用说明

1. 在左侧选择对应费用类型上传文件。
2. 报销单首页会自动出现在右侧预览第一张。
3. 在“报销单信息”中填写公司名、部门、姓名、事由 / 项目。
4. 如需填写起止时间和地点，可直接在报销单表格内编辑，并可新增行。
5. OCR 回填后请人工检查金额、时间、地点是否正确。
6. 点击“打印”进入独立打印页，再确认打印。

## 报销单信息缓存

以下字段会自动保存在浏览器本地：

- 公司名
- 部门
- 姓名
- 事由 / 项目

缓存使用 `localStorage.invoiceExpenseForm`。如果要清空，可以在浏览器开发者工具中删除该项。

公司名默认为空。为空时，打印页不会显示公司名标题，方便公开部署或多人共用。

## 多语言

语言包集中在 `i18n.js`。

支持 URL 参数指定语言：

```text
http://127.0.0.1:4173/?lang=en
http://127.0.0.1:4173/?lang=ja
```

支持的语言代码：

- `zh-CN`
- `zh-TW`
- `en`
- `ja`
- `ko`
- `de`
- `fr`
- `es`

## Docker 常用命令

启动或更新：

```bash
docker compose up --build -d
```

查看日志：

```bash
docker compose logs -f
```

停止服务：

```bash
docker compose down
```

如果需要删除 OCR 模型缓存卷：

```bash
docker compose down -v
```

## 项目结构

```text
.
├── index.html          # 主页面
├── print.html          # 独立打印页
├── i18n.js             # 多语言字典和 i18n 工具
├── ocr_server.py       # 本地 OCR 服务
├── requirements.txt    # Python 依赖
├── Dockerfile
├── docker-compose.yml
├── favicon.svg
├── favicon.ico
├── icon-192.png
├── icon-512.png
└── site.webmanifest
```

## 隐私说明

默认部署方式下，上传文件只在本地浏览器预览，并发送到本机 OCR 服务识别。请不要把服务暴露到公网，除非你已经增加了访问控制。

## License

MIT

# video-auto-editor

基于 FastAPI + Streamlit 的视频自动剪辑系统，支持多视频拼接、去音轨、音频合成，自动生成最终视频。

## 功能特性

- **多视频上传**：支持同时上传多个 MP4 视频文件
- **音频上传**：支持上传 MP3、WAV 格式的音频文件
- **视频拼接**：将多个视频自动拼接成一个
- **去音轨**：去除原视频的音频轨道
- **音频合成**：将上传的音频与拼接后的视频合并
- **自动清理**：下载完成后自动清理临时文件

## 项目结构

```
video-auto-editor/
├── src/                    # 后端源代码
│   ├── api/               # API 路由和数据模型
│   ├── core/              # 配置文件
│   └── services/          # 业务逻辑服务
├── streamlit_app/         # 前端 Streamlit 应用
├── tmps/                  # 临时文件目录
├── pyproject.toml         # 项目依赖配置
└── requirements.txt      # 锁定后的依赖
```

## 环境要求

- Python 3.13+
- ffmpeg

## 本地开发

### 1. 安装依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
uv sync
```

### 2. 启动后端服务

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8081
```

### 3. 启动前端服务

在另一个终端运行：

```bash
streamlit run streamlit_app/app.py --server.port 8501
```

### 4. 访问应用

打开浏览器访问 http://localhost:8501

## Docker 部署

### 构建并启动

```bash
docker-compose up -d --build
```

### 查看日志

```bash
docker-compose logs -f
```

### 停止服务

```bash
docker-compose down
```

### 访问应用

- **前端**：http://localhost:8501
- **后端 API**：http://localhost:8081
- **API 文档**：http://localhost:8081/docs

## 使用流程

1. **步骤1**：上传多个 MP4 视频文件
2. **步骤2**：上传一个 MP3 或 WAV 音频文件
3. **步骤3**：点击「开始剪辑」，等待处理完成
4. **步骤4**：点击「下载合成视频」，文件自动下载，临时文件自动清理

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/upload/videos` | 上传多个视频文件 |
| POST | `/upload/audio` | 上传单个音频文件 |
| POST | `/process` | 执行视频处理（SSE 流式响应） |
| GET | `/download/{file_id}` | 下载合成视频 |
| POST | `/cleanup` | 清理指定临时文件 |

## 配置说明

配置文件位于 `src/core/config.py`：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `API_PORT` | 8081 | API 服务端口 |
| `MAX_FILE_SIZE` | 500MB | 单文件大小限制 |
| `CORS_ORIGINS` | localhost:8501 | 允许的跨域来源 |

## 技术栈

- **后端**：FastAPI + uvicorn + ffmpeg-python
- **前端**：Streamlit
- **依赖管理**：uv

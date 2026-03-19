# 视频自动剪辑系统 - 开发需求文档

## 1. 项目概述

### 1.1 项目名称
`video-auto-editor`

### 1.2 项目简介
基于 FastAPI 后端 + Streamlit 前端的视频自动剪辑系统，支持多视频拼接、去音轨、音频合成及打包下载。

### 1.3 核心功能
- 多 MP4 视频文件批量上传并按顺序拼接
- 去除拼接后视频的原始音频轨道
- 单个 MP3/WAV 音频文件作为新音轨合成
- 生成最终视频文件并提供下载

---

## 2. 技术架构

### 2.1 技术栈
| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 后端框架 | FastAPI | 提供 RESTful API |
| 前端框架 | Streamlit | 交互式 Web 界面 |
| 视频处理 | FFmpeg (via ffmpeg-python) | 视频拼接、去音轨、合成 |
| 文件存储 | 本地临时文件 | 使用 `/tmp` 目录，进程结束时清理 |
| 进程管理 | Uvicorn | ASGI 服务器 |

### 2.2 架构图
```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  视频上传入口  │  │  音频上传入口  │  │   下载按钮    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────▲───────┘  │
└─────────┼──────────────────┼─────────────────┼──────────┘
          │                  │                 │
          ▼                  ▼                 │
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Backend                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  视频上传API  │  │  音频上传API  │  │  视频处理API  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                │                 │           │
│         ▼                ▼                 ▼           │
│  ┌─────────────────────────────────────────────────────┐│
│  │              VideoProcessingService                  ││
│  │  - 视频拼接 (concatenate_videos)                    ││
│  │  - 去除音轨 (remove_audio)                          ││
│  │  - 音视频合成 (merge_audio_video)                   ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 3. 功能模块详细设计

### 3.1 前端模块 (Streamlit)

#### 3.1.1 页面布局
```
┌─────────────────────────────────────────────────────────┐
│  🎬 视频自动剪辑系统                                      │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐│
│  │  步骤1: 上传视频文件 (MP4)                            ││
│  │  [支持多选] [已选择: X 个文件]                        ││
│  │  ┌─────┐ ┌─────┐ ┌─────┐                           ││
│  │  │ 📹  │ │ 📹  │ │ 📹  │ ...                        ││
│  │  │file1│ │file2│ │file3│                           ││
│  │  └─────┘ └─────┘ └─────┘                           ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  步骤2: 上传音频文件 (MP3/WAV)                        ││
│  │  [支持单选]                                          ││
│  │  ┌─────────────────┐                                 ││
│  │  │     🎵          │                                 ││
│  │  │   audio.mp3    │                                 ││
│  │  └─────────────────┘                                 ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  步骤3: 开始处理                                     ││
│  │  [━━━━━━━━━━━░░░░░░░░░░] 50%  拼接视频中...          ││
│  │  [开始剪辑]  [清空重置]                              ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  步骤4: 下载结果                                     ││
│  │  [📥 下载合成视频]                                   ││
│  │  文件名: final_video.mp4 | 大小: XX MB              ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

#### 3.1.2 组件说明

| 组件 | 类型 | 功能描述 |
|------|------|----------|
| 视频上传区 | `st.file_uploader` | `type=["mp4"]`, `accept_multiple_files=True` |
| 音频上传区 | `st.file_uploader` | `type=["mp3", "wav"]`, `accept_multiple_files=False` |
| 处理按钮 | `st.button` | 触发后端视频处理流程 |
| 进度条 | `st.progress` | 显示处理进度百分比 |
| 状态文本 | `st.text` | 显示当前处理步骤 |
| 下载按钮 | `st.download_button` | 下载最终生成的视频文件 |
| 清空按钮 | `st.button` | 重置所有状态和已上传文件 |

### 3.2 后端模块 (FastAPI)

#### 3.2.1 API 端点

| 端点 | 方法 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| `POST /upload/videos` | POST | 上传多个视频文件 | `Multipart/form-data` (多个文件) | `{ "file_ids": ["uuid1", "uuid2"] }` |
| `POST /upload/audio` | POST | 上传单个音频文件 | `Multipart/form-data` (单个文件) | `{ "file_id": "uuid3" }` |
| `POST /process` | POST | 执行视频处理 | `{ "video_ids": [...], "audio_id": "uuid3" }` | `JSON Stream` (进度更新) |
| `GET /download/{file_id}` | GET | 下载生成的视频 | - | `application/octet-stream` |
| `DELETE /cleanup/{file_id}` | DELETE | 清理临时文件 | - | `{ "status": "ok" }` |

#### 3.2.2 数据模型

```python
# 请求模型
class ProcessRequest(BaseModel):
    video_ids: List[str]  # 按顺序排列的视频文件ID
    audio_id: str          # 音频文件ID

# 响应模型
class UploadResponse(BaseModel):
    file_ids: List[str] | str  # 上传成功后返回的文件ID
    filename: str              # 原始文件名

class ProcessStatus(BaseModel):
    status: Literal["processing", "completed", "error"]
    progress: float             # 0.0 ~ 1.0
    message: str               # 当前步骤描述
    result_file_id: str | None # 处理完成后的文件ID
```

#### 3.2.3 文件存储策略

| 阶段 | 存储位置 | 生命周期 |
|------|----------|----------|
| 上传文件 | `/tmp/video_editor/uploads/{file_id}.{ext}` | 直到处理完成或手动清理 |
| 中间文件 | `/tmp/video_editor/process/{task_id}/` | 处理完成后自动清理 |
| 最终文件 | `/tmp/video_editor/output/{task_id}_final.mp4` | 直到下载完成或超时清理 |

#### 3.2.4 视频处理流程

```
1. 接收请求
   └── 验证 video_ids 列表和 audio_id 存在

2. 视频拼接 (concatenate_videos)
   ├── 读取所有视频文件
   ├── 生成 FFmpeg concat demuxer 文件 (filelist.txt)
   ├── 执行: ffmpeg -f concat -safe 0 -i filelist.txt -c copy merged_video.mp4
   └── 输出: merged_video.mp4

3. 去除音轨 (remove_audio)
   └── 执行: ffmpeg -i merged_video.mp4 -c:v copy -an silent_video.mp4

4. 音视频合成 (merge_audio_video)
   ├── 读取处理后的无声视频
   ├── 读取上传的音频文件
   └── 执行: ffmpeg -i silent_video.mp4 -i audio.mp3 -c:v copy -c:a aac -shortest final_video.mp4

5. 返回结果
   └── 返回 final_file_id 给前端
```

### 3.3 错误处理

| 错误场景 | HTTP 状态码 | 错误信息 |
|----------|-------------|----------|
| 未上传视频 | 400 | "请先上传至少一个视频文件" |
| 未上传音频 | 400 | "请先上传音频文件" |
| 视频文件读取失败 | 500 | "视频文件格式错误或已损坏" |
| 音频文件读取失败 | 500 | "音频文件格式错误或已损坏" |
| FFmpeg 执行失败 | 500 | "视频处理失败: {具体错误}" |
| 文件不存在 | 404 | "文件不存在或已过期" |

---

## 4. 视频处理模块详细设计

### 4.1 核心类: `VideoProcessingService`

```python
class VideoProcessingService:
    """视频处理服务"""

    def __init__(self, temp_dir: str = "/tmp/video_editor"):
        self.temp_dir = Path(temp_dir)
        self.uploads_dir = self.temp_dir / "uploads"
        self.process_dir = self.temp_dir / "process"
        self.output_dir = self.temp_dir / "output"
        self._ensure_dirs()

    def concatenate_videos(self, video_paths: List[Path], output_path: Path) -> bool:
        """拼接多个视频文件"""

    def remove_audio(self, video_path: Path, output_path: Path) -> bool:
        """去除视频音轨"""

    def merge_audio_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path
    ) -> bool:
        """合并音视频"""

    def process(
        self,
        video_ids: List[str],
        audio_id: str,
        progress_callback: Callable[[float, str], None] = None
    ) -> Path:
        """完整处理流程"""
```

### 4.2 FFmpeg 命令参考

```bash
# 1. 视频拼接 (使用 concat demuxer)
ffmpeg -f concat -safe 0 -i filelist.txt -c copy merged.mp4

# 2. 去除音轨
ffmpeg -i merged.mp4 -c:v copy -an silent.mp4

# 3. 音视频合并
ffmpeg -i silent.mp4 -i audio.mp3 -c:v copy -c:a aac -shortest final.mp4
```

---

## 5. 前端交互流程

### 5.1 用户操作流程

```
1. 用户打开页面
   └── 显示空的上传区域

2. 用户上传视频文件 (支持拖拽)
   └── 前端显示已上传文件列表和缩略图

3. 用户上传音频文件
   └── 前端显示已上传音频文件名

4. 用户点击 [开始剪辑]
   └── 前端: 禁用上传区域，显示进度条
   └── 后端: 调用 /process 接口
   └── 后端: SSE 流式返回处理进度
   └── 前端: 实时更新进度条和状态文本

5. 处理完成
   └── 前端: 显示 [下载合成视频] 按钮
   └── 后端: 生成的可下载文件存储在 output 目录

6. 用户点击 [下载合成视频]
   └── 浏览器下载 final_video.mp4

7. 用户点击 [清空重置]
   └── 前端: 重置所有状态
   └── 后端: 调用 /cleanup 清理临时文件
```

### 5.2 进度回调机制

使用 Server-Sent Events (SSE) 实现实时进度推送：

```python
# 后端
async def process_endpoint(request: ProcessRequest):
    async def event_generator():
        for progress, message in process_with_progress(request):
            yield f"data: {json.dumps({'progress': progress, 'message': message})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 6. 项目结构

```
video-auto-editor/
├── SPEC.md                    # 本文档
├── requirements.txt           # Python 依赖
├── pyproject.toml             # 项目配置
├── .python-version            # Python 版本
├── src/
│   ├── __init__.py
│   ├── main.py                # FastAPI 应用入口
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # API 路由定义
│   │   └── models.py          # Pydantic 模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_manager.py    # 文件管理服务
│   │   └── video_processor.py # 视频处理服务
│   └── core/
│       ├── __init__.py
│       └── config.py          # 配置项
├── streamlit_app/
│   ├── __init__.py
│   └── app.py                 # Streamlit 前端入口
└── tests/
    ├── __init__.py
    ├── test_video_processor.py
    └── test_api.py
```

---

## 7. 依赖清单

```
# requirements.txt

fastapi>=0.109.0
uvicorn[standard]>=0.27.0
streamlit>=1.30.0
ffmpeg-python>=0.2.0
python-multipart>=0.0.6
pydantic>=2.0.0
aiofiles>=23.0.0
```

> **注意**: 系统需要预装 FFmpeg，建议 Ubuntu/Debian: `apt install ffmpeg`，macOS: `brew install ffmpeg`

---

## 8. 部署指南

### 8.1 开发环境启动

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 安装依赖
uv sync

# 3. 启动 FastAPI 后端 (终端1)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 4. 启动 Streamlit 前端 (终端2)
streamlit run streamlit_app/app.py --server.port 8501 --server.address http://localhost
```

### 8.2 访问地址

| 服务 | 地址 |
|------|------|
| Streamlit 前端 | http://localhost:8501 |
| FastAPI 文档 | http://localhost:8000/docs |

---

## 9. 非功能性需求

### 9.1 性能要求
- 支持处理总时长不超过 30 分钟的视频文件
- 单个视频文件大小不超过 500MB
- 处理进度实时更新，间隔不超过 1 秒

### 9.2 安全要求
- 临时文件存储在 `/tmp` 目录，避免污染项目目录
- 文件上传仅接受指定的 MIME 类型
- 处理完成后自动清理临时文件

### 9.3 兼容性要求
- 浏览器: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- 操作系统: Windows/macOS/Linux (需安装 FFmpeg)

---

## 10. 验收标准

| 序号 | 验收项 | 验收条件 |
|------|--------|----------|
| 1 | 视频上传 | 可选择多个 MP4 文件，显示已上传列表 |
| 2 | 音频上传 | 可选择单个 MP3 或 WAV 文件 |
| 3 | 视频拼接 | 多个视频按上传顺序拼接为一个视频 |
| 4 | 去音轨 | 拼接后的视频无原始声音 |
| 5 | 音视频合成 | 最终视频包含上传的音频 |
| 6 | 进度显示 | 处理过程中显示实时进度 |
| 7 | 下载功能 | 可下载最终生成的 MP4 文件 |
| 8 | 错误处理 | 上传非 MP4/MP3/WAV 文件时提示错误 |
| 9 | 清理功能 | 点击清空后重置界面和临时文件 |

---

## 11. 后续扩展点 (暂不实现)

- [ ] 支持更多视频格式 (AVI, MOV, MKV)
- [ ] 支持裁剪视频片段
- [ ] 添加视频特效 (转场、滤镜)
- [ ] 支持添加字幕
- [ ] 处理队列和任务历史

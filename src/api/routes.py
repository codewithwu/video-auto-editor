"""API 路由"""
import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse, StreamingResponse

from src.api.models import CleanupResponse, ProcessRequest, ProcessStatus, UploadResponse
from src.core.config import config
from src.services.file_manager import file_manager
from src.services.video_processor import video_processor

app = FastAPI()


@app.post("/upload/videos", response_model=UploadResponse)
async def upload_videos(files: list[UploadFile] = File(...)):
    """上传多个视频文件

    Args:
        files: 视频文件列表

    Returns:
        上传成功的文件ID列表
    """
    if not files:
        raise HTTPException(status_code=400, detail="请先上传至少一个视频文件")

    file_ids = []
    filenames = []

    for file in files:
        if not file.filename:
            continue

        # 验证文件类型
        ext = Path(file.filename).suffix.lower()
        if ext.lstrip(".") not in config.VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的视频格式: {ext}，仅支持 MP4",
            )

        # 读取并保存文件
        content = await file.read()
        if len(content) > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件 {file.filename} 超过大小限制 (500MB)",
            )

        file_id = await file_manager.save_uploaded_file(content, file.filename)
        file_ids.append(file_id)
        filenames.append(file.filename)

    return UploadResponse(file_ids=file_ids, filename=", ".join(filenames))


@app.post("/upload/audio", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    """上传单个音频文件

    Args:
        file: 音频文件

    Returns:
        上传成功的文件ID
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="请先上传音频文件")

    # 验证文件类型
    ext = Path(file.filename).suffix.lower()
    if ext.lstrip(".") not in config.AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的音频格式: {ext}，仅支持 MP3、WAV",
        )

    # 读取并保存文件
    content = await file.read()
    if len(content) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件 {file.filename} 超过大小限制 (500MB)",
        )

    file_id = await file_manager.save_uploaded_file(content, file.filename)

    return UploadResponse(file_ids=file_id, filename=file.filename)


@app.post("/process")
async def process_videos(request: ProcessRequest):
    """执行视频处理

    Args:
        request: 处理请求，包含视频ID列表和音频ID

    Returns:
        SSE 流式响应，包含处理进度
    """
    video_ids = request.video_ids
    audio_id = request.audio_id

    if not video_ids:
        raise HTTPException(status_code=400, detail="请先上传至少一个视频文件")

    if not audio_id:
        raise HTTPException(status_code=400, detail="请先上传音频文件")

    # 获取文件路径
    try:
        video_paths = [file_manager.get_file_path(vid) for vid in video_ids]
        audio_path = file_manager.get_file_path(audio_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 验证文件存在
    for path in video_paths:
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"视频文件不存在或已过期: {path}")
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"音频文件不存在或已过期: {audio_path}")

    # 进度回调生成器
    def progress_callback(progress: float, message: str) -> None:
        pass  # 在生成器中使用 nonlocal 需要通过其他方式传递

    async def event_generator():
        nonlocal video_paths, audio_path

        # 步骤 1: 拼接视频 (0% - 30%)
        def on_concat_progress(p: float, msg: str) -> None:
            current_progress = p * 0.3  # 0-0.3
            status = ProcessStatus(
                status="processing",
                progress=current_progress,
                message=f"拼接视频中... ({video_paths.index(Path(msg)) + 1}/{len(video_paths)})" if "拼接" in msg else msg,
            )
            yield f"data: {json.dumps(status.model_dump())}\n\n"

        try:
            # 拼接视频
            import uuid

            task_id = str(uuid.uuid4())
            process_dir = config.PROCESS_DIR / task_id
            process_dir.mkdir(parents=True, exist_ok=True)
            merged_video = process_dir / "merged_video.mp4"

            # 发送开始状态
            yield f"data: {json.dumps({'status': 'processing', 'progress': 0.0, 'message': '开始拼接视频...'})}\n\n"

            # 创建 concat demuxer 文件
            filelist_path = process_dir / "filelist.txt"
            with open(filelist_path, "w") as f:
                for vp in video_paths:
                    escaped_path = str(vp).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            import subprocess

            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(filelist_path), "-c", "copy", str(merged_video)],
                check=True,
                capture_output=True,
            )

            yield f"data: {json.dumps({'status': 'processing', 'progress': 0.3, 'message': '视频拼接完成'})}\n\n"

            # 步骤 2: 去除音轨 (30% - 60%)
            silent_video = process_dir / "silent_video.mp4"

            yield f"data: {json.dumps({'status': 'processing', 'progress': 0.35, 'message': '去除原始音轨...'})}\n\n"

            import ffmpeg

            stream = ffmpeg.input(str(merged_video))
            stream = ffmpeg.output(stream, str(silent_video), vcodec="copy", an=None)
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            yield f"data: {json.dumps({'status': 'processing', 'progress': 0.6, 'message': '去除音轨完成'})}\n\n"

            # 步骤 3: 音视频合成 (60% - 100%)
            final_video = process_dir / "final_video.mp4"

            yield f"data: {json.dumps({'status': 'processing', 'progress': 0.65, 'message': '合成音频与视频...'})}\n\n"

            video_stream = ffmpeg.input(str(silent_video))
            audio_stream = ffmpeg.input(str(audio_path))
            stream = ffmpeg.output(video_stream, audio_stream, str(final_video), vcodec="copy", acodec="aac", shortest=None)
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            # 移动到输出目录
            output_file_id = str(uuid.uuid4())
            final_output = config.OUTPUT_DIR / f"{output_file_id}_final.mp4"
            final_video.rename(final_output)

            # 清理中间文件
            import shutil

            if process_dir.exists():
                shutil.rmtree(process_dir)

            # 发送完成状态
            yield f"data: {json.dumps({'status': 'completed', 'progress': 1.0, 'message': '处理完成', 'result_file_id': output_file_id})}\n\n"

        except subprocess.CalledProcessError as e:
            yield f"data: {json.dumps({'status': 'error', 'progress': 0.0, 'message': f'视频处理失败: {e.stderr.decode()}'})}\n\n"
        except ffmpeg.Error as e:
            yield f"data: {json.dumps({'status': 'error', 'progress': 0.0, 'message': f'视频处理失败: {e.stderr.decode()}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'progress': 0.0, 'message': f'处理异常: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """下载生成的文件

    Args:
        file_id: 文件ID

    Returns:
        文件流响应
    """
    try:
        # 查找输出目录中的文件
        for f in config.OUTPUT_DIR.glob(f"{file_id}_*.mp4"):
            return FileResponse(path=f, filename=f.name, media_type="application/octet-stream")

        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在或已过期")


@app.delete("/cleanup/{file_id}", response_model=CleanupResponse)
async def cleanup_file(file_id: str = None):
    """清理临时文件

    Args:
        file_id: 文件ID，为空时清理所有上传文件

    Returns:
        清理状态
    """
    try:
        if file_id:
            # 清理指定文件
            file_manager.delete_file(file_id)
        else:
            # 清理所有上传文件
            import shutil

            for d in [config.UPLOADS_DIR, config.OUTPUT_DIR]:
                if d.exists():
                    for f in d.glob("*"):
                        if f.is_file():
                            f.unlink()

        return CleanupResponse(status="ok")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

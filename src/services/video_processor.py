"""视频处理服务"""
import subprocess
import uuid
from pathlib import Path
from typing import Callable, Optional

import ffmpeg

from src.core.config import config


class VideoProcessingService:
    """视频处理服务"""

    def __init__(self) -> None:
        self.temp_dir = config.TEMP_DIR
        self.process_dir = config.PROCESS_DIR
        self.output_dir = config.OUTPUT_DIR

    def _ensure_dirs(self) -> None:
        """确保目录结构存在"""
        self.process_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def concatenate_videos(
        self,
        video_paths: list[Path],
        output_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> bool:
        """拼接多个视频文件

        Args:
            video_paths: 视频文件路径列表
            output_path: 输出文件路径
            progress_callback: 进度回调函数

        Returns:
            是否成功
        """
        if progress_callback:
            progress_callback(0.0, "开始拼接视频...")

        if len(video_paths) == 1:
            # 只有一个视频时，直接复制
            video_paths[0].rename(output_path)
            if progress_callback:
                progress_callback(1.0, "视频拼接完成")
            return True

        # 创建 concat demuxer 文件列表
        task_id = str(uuid.uuid4())
        process_dir = self.process_dir / task_id
        process_dir.mkdir(parents=True, exist_ok=True)

        filelist_path = process_dir / "filelist.txt"

        with open(filelist_path, "w") as f:
            for video_path in video_paths:
                # 转义文件路径中的单引号
                escaped_path = str(video_path).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        # 执行 FFmpeg concat
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(filelist_path),
                    "-c",
                    "copy",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
            )
            if progress_callback:
                progress_callback(1.0, "视频拼接完成")
            return True
        except subprocess.CalledProcessError as e:
            if progress_callback:
                progress_callback(0.0, f"视频拼接失败: {e.stderr.decode()}")
            return False

    def remove_audio(
        self,
        video_path: Path,
        output_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> bool:
        """去除视频音轨

        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            progress_callback: 进度回调函数

        Returns:
            是否成功
        """
        if progress_callback:
            progress_callback(0.0, "去除原始音轨...")

        try:
            # 使用 ffmpeg-python 去除音频
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(stream, str(output_path), vcodec="copy", an=None)
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            if progress_callback:
                progress_callback(1.0, "去除音轨完成")
            return True
        except ffmpeg.Error as e:
            if progress_callback:
                progress_callback(0.0, f"去除音轨失败: {e.stderr.decode()}")
            return False

    def merge_audio_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> bool:
        """合并音视频

        Args:
            video_path: 视频路径
            audio_path: 音频路径
            output_path: 输出路径
            progress_callback: 进度回调函数

        Returns:
            是否成功
        """
        if progress_callback:
            progress_callback(0.0, "合成音频与视频...")

        try:
            # 使用 ffmpeg-python 合并
            video_stream = ffmpeg.input(str(video_path))
            audio_stream = ffmpeg.input(str(audio_path))
            stream = ffmpeg.output(
                video_stream,
                audio_stream,
                str(output_path),
                vcodec="copy",
                acodec="aac",
                shortest=None,
            )
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            if progress_callback:
                progress_callback(1.0, "音视频合成完成")
            return True
        except ffmpeg.Error as e:
            if progress_callback:
                progress_callback(0.0, f"音视频合成失败: {e.stderr.decode()}")
            return False

    def process(
        self,
        video_paths: list[Path],
        audio_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """完整视频处理流程

        Args:
            video_paths: 视频文件路径列表
            audio_path: 音频文件路径
            progress_callback: 进度回调函数

        Returns:
            最终输出文件路径
        """
        task_id = str(uuid.uuid4())
        process_dir = self.process_dir / task_id
        process_dir.mkdir(parents=True, exist_ok=True)

        # 1. 拼接视频
        merged_video = process_dir / "merged_video.mp4"
        if not self.concatenate_videos(video_paths, merged_video, progress_callback):
            raise RuntimeError("视频拼接失败")

        # 2. 去除音轨
        silent_video = process_dir / "silent_video.mp4"
        if not self.remove_audio(merged_video, silent_video, progress_callback):
            raise RuntimeError("去除音轨失败")

        # 3. 合并音视频
        final_video = process_dir / "final_video.mp4"
        if not self.merge_audio_video(silent_video, audio_path, final_video, progress_callback):
            raise RuntimeError("音视频合成失败")

        # 移动到输出目录
        output_file_id = str(uuid.uuid4())
        final_output = self.output_dir / f"{output_file_id}_final.mp4"
        final_video.rename(final_output)

        # 清理中间文件
        self._cleanup_process_dir(process_dir)

        return final_output

    def _cleanup_process_dir(self, process_dir: Path) -> None:
        """清理处理目录"""
        import shutil

        if process_dir.exists():
            shutil.rmtree(process_dir)


# 全局视频处理服务实例
video_processor = VideoProcessingService()
video_processor._ensure_dirs()

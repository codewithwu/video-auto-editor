"""文件管理服务"""
import shutil
import uuid
from pathlib import Path
from typing import Optional

import aiofiles

from src.core.config import config


class FileManager:
    """文件管理服务"""

    def __init__(self) -> None:
        self.temp_dir = config.TEMP_DIR
        self.uploads_dir = config.UPLOADS_DIR
        self.process_dir = config.PROCESS_DIR
        self.output_dir = config.OUTPUT_DIR

    def _ensure_dirs(self) -> None:
        """确保目录结构存在"""
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.process_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def save_uploaded_file(
        self,
        file_content: bytes,
        filename: str,
        subdir: str = "uploads",
    ) -> str:
        """保存上传的文件

        Args:
            file_content: 文件内容
            filename: 原始文件名
            subdir: 子目录名

        Returns:
            文件ID (不含扩展名)
        """
        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix.lower()

        if subdir == "uploads":
            save_dir = self.uploads_dir
        elif subdir == "output":
            save_dir = self.output_dir
        else:
            save_dir = self.process_dir / subdir

        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / f"{file_id}{ext}"

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        return file_id

    def get_file_path(self, file_id: str, subdir: str = "uploads") -> Path:
        """获取文件路径

        Args:
            file_id: 文件ID
            subdir: 子目录名

        Returns:
            文件完整路径
        """
        if subdir == "uploads":
            search_dir = self.uploads_dir
        elif subdir == "output":
            search_dir = self.output_dir
        else:
            search_dir = self.process_dir / subdir

        # 查找具有给定 ID 的文件
        for ext in config.VIDEO_EXTENSIONS | config.AUDIO_EXTENSIONS:
            file_path = search_dir / f"{file_id}.{ext}"
            if file_path.exists():
                return file_path

        # 如果没找到，尝试在 uploads 中查找
        for ext in config.VIDEO_EXTENSIONS | config.AUDIO_EXTENSIONS:
            file_path = self.uploads_dir / f"{file_id}.{ext}"
            if file_path.exists():
                return file_path

        raise FileNotFoundError(f"File not found: {file_id}")

    def delete_file(self, file_id: str, subdir: str = "uploads") -> bool:
        """删除文件

        Args:
            file_id: 文件ID
            subdir: 子目录名

        Returns:
            是否删除成功
        """
        try:
            file_path = self.get_file_path(file_id, subdir)
            file_path.unlink()
            return True
        except FileNotFoundError:
            return False

    def cleanup_task(self, task_id: str) -> None:
        """清理任务目录

        Args:
            task_id: 任务ID
        """
        task_dir = self.process_dir / task_id
        if task_dir.exists():
            shutil.rmtree(task_dir)

    def get_output_file_path(self, file_id: str) -> Path:
        """获取输出文件路径

        Args:
            file_id: 文件ID

        Returns:
            文件完整路径
        """
        file_path = self.output_dir / f"{file_id}.mp4"
        if not file_path.exists():
            raise FileNotFoundError(f"Output file not found: {file_id}")
        return file_path


# 全局文件管理器实例
file_manager = FileManager()
file_manager._ensure_dirs()

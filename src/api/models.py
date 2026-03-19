"""Pydantic 数据模型"""
from typing import Literal, Optional

from pydantic import BaseModel


class ProcessRequest(BaseModel):
    """视频处理请求"""

    video_ids: list[str]
    audio_id: str


class UploadResponse(BaseModel):
    """文件上传响应"""

    file_ids: list[str] | str
    filename: str


class ProcessStatus(BaseModel):
    """处理状态"""

    status: Literal["processing", "completed", "error"]
    progress: float
    message: str
    result_file_id: Optional[str] = None


class CleanupResponse(BaseModel):
    """清理响应"""

    status: str

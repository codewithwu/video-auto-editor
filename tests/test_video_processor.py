"""视频处理服务单元测试"""
import subprocess
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.video_processor import VideoProcessingService


class TestVideoProcessingService:
    """视频处理服务测试类"""

    @pytest.fixture
    def service(self, tmp_path):
        """创建测试服务实例"""
        service = VideoProcessingService()
        service.temp_dir = tmp_path
        service.process_dir = tmp_path / "process"
        service.output_dir = tmp_path / "output"
        service._ensure_dirs()
        return service

    @pytest.fixture
    def sample_video(self, tmp_path):
        """创建示例视频文件"""
        video_path = tmp_path / "sample_video.mp4"
        video_path.write_bytes(b"fake video content")
        return video_path

    def test_ensure_dirs(self, service, tmp_path):
        """测试目录创建"""
        assert service.process_dir.exists()
        assert service.output_dir.exists()

    def test_concatenate_videos_single(self, service, tmp_path, sample_video):
        """测试单个视频拼接"""
        output_path = tmp_path / "output.mp4"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            result = service.concatenate_videos([sample_video], output_path)

        assert result is True
        assert output_path.exists() or mock_run.called

    def test_concatenate_videos_multiple(self, service, tmp_path):
        """测试多个视频拼接"""
        videos = []
        for i in range(3):
            video_path = tmp_path / f"video_{i}.mp4"
            video_path.write_bytes(b"fake video content")
            videos.append(video_path)

        output_path = tmp_path / "merged.mp4"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            result = service.concatenate_videos(videos, output_path)

        assert result is True
        mock_run.assert_called_once()

        # 验证 concat demuxer 文件被创建
        call_args = mock_run.call_args[0][0]
        assert "-f" in call_args and "concat" in call_args

    def test_remove_audio(self, service, tmp_path, sample_video):
        """测试去除音轨"""
        output_path = tmp_path / "silent.mp4"

        with patch("ffmpeg.run") as mock_run:
            mock_run.return_value = None
            result = service.remove_audio(sample_video, output_path)

        assert result is True
        mock_run.assert_called_once()

    def test_merge_audio_video(self, service, tmp_path, sample_video):
        """测试音视频合并"""
        audio_path = tmp_path / "audio.mp3"
        audio_path.write_bytes(b"fake audio content")

        output_path = tmp_path / "final.mp4"

        with patch("ffmpeg.run") as mock_run:
            mock_run.return_value = None
            result = service.merge_audio_video(sample_video, audio_path, output_path)

        assert result is True
        mock_run.assert_called_once()


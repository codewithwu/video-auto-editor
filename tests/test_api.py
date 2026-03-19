"""API 单元测试"""
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.routes import app


class TestAPI:
    """API 测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_upload_videos_invalid_type(self, client):
        """测试上传不支持的文件类型"""
        files = [("files", ("test.txt", io.BytesIO(b"test content"), "text/plain"))]
        response = client.post("/upload/videos", files=files)
        assert response.status_code == 400

    def test_upload_audio_invalid_type(self, client):
        """测试上传不支持的音频格式"""
        files = [("file", ("test.ogg", io.BytesIO(b"test content"), "audio/ogg"))]
        response = client.post("/upload/audio", files=files)
        assert response.status_code == 400

    def test_process_no_videos(self, client):
        """测试未上传视频时处理"""
        response = client.post("/process", json={"video_ids": [], "audio_id": "test"})
        assert response.status_code == 400

    def test_process_no_audio(self, client):
        """测试未上传音频时处理"""
        response = client.post("/process", json={"video_ids": ["vid1"], "audio_id": ""})
        assert response.status_code == 400

    def test_cleanup_success(self, client):
        """测试清理文件"""
        with patch("src.api.routes.file_manager") as mock_file_manager:
            mock_file_manager.delete_file.return_value = True

            response = client.delete("/cleanup/test-file-id")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

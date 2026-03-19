"""配置文件"""
from pathlib import Path


def _get_project_root() -> Path:
    """获取项目根目录（基于 config.py 的位置）"""
    # config.py 位于 src/core/config.py，所以 parent.parent.parent 就是项目根目录
    return Path(__file__).parent.parent.parent


class Config:
    """应用配置"""

    PROJECT_ROOT: Path = _get_project_root()
    TEMP_DIR: Path = PROJECT_ROOT / "tmps"
    UPLOADS_DIR: Path = TEMP_DIR / "uploads"
    PROCESS_DIR: Path = TEMP_DIR / "process"
    OUTPUT_DIR: Path = TEMP_DIR / "output"

    # API 配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS 配置
    CORS_ORIGINS: list[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]

    # 支持的文件类型
    VIDEO_EXTENSIONS: set[str] = {"mp4", "avi", "mov", "mkv"}
    AUDIO_EXTENSIONS: set[str] = {"mp3", "wav"}

    # 文件大小限制 (字节)
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB

    def _ensure_dirs(self) -> None:
        """确保目录结构存在"""
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.PROCESS_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 全局配置实例
config = Config()
config._ensure_dirs()

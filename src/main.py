"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import app as routes_app
from src.core.config import config

# 创建 FastAPI 应用
app = FastAPI(
    title="视频自动剪辑系统",
    description="基于 FastAPI 后端 + Streamlit 前端的视频自动剪辑系统",
    version="0.1.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.mount("/", routes_app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )

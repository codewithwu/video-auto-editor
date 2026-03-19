FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# 安装 ffmpeg 和其他系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 

# 复制源代码
COPY src/ ./src/
COPY streamlit_app/ ./streamlit_app/

# 创建临时目录
RUN mkdir -p /app/tmps/uploads /app/tmps/process /app/tmps/output && \
    chmod -R 777 /app/tmps

# 暴露端口
EXPOSE 8081 8501

# 启动命令：运行后端和前端
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port 8081 & streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0"]
# video-auto-editor
基于 FastAPI + Streamlit 的视频自动剪辑系统，支持多视频拼接、去音轨、音频合成，自动生成最终视频。
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

streamlit run streamlit_app/app.py --server.port 8501
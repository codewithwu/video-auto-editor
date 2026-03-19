"""Streamlit 前端应用"""
import requests
import streamlit as st

# 配置页面
st.set_page_config(
    page_title="视频自动剪辑系统",
    page_icon="🎬",
    layout="wide",
)

# API 地址
API_BASE_URL = "http://localhost:8001"


def init_session_state():
    """初始化会话状态"""
    defaults = {
        "video_ids": [],
        "audio_id": None,
        "audio_filename": None,
        "result_file_id": None,
        "processing": False,
        "video_filenames": [],
        "video_uploaded": False,
        "audio_uploaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def upload_videos_to_api(files):
    """上传视频文件到 API"""
    if not files:
        return False, []

    # 文件大小限制 500MB
    MAX_SIZE = 500 * 1024 * 1024
    for f in files:
        if f.size > MAX_SIZE:
            st.error(f"文件 {f.name} 超过大小限制 (500MB)")
            return False, []

    try:
        files_data = []
        for f in files:
            files_data.append(("files", (f.name, f.getvalue(), f.type)))

        response = requests.post(
            f"{API_BASE_URL}/upload/videos",
            files=files_data,
            timeout=300,
        )

        if response.status_code == 200:
            data = response.json()
            file_ids = data.get("file_ids", [])
            return True, file_ids
        else:
            error_msg = response.json().get("detail", "上传失败")
            st.error(f"视频上传失败: {error_msg}")
            return False, []
    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务，请确保 FastAPI 服务已启动")
        return False, []
    except Exception as e:
        st.error(f"视频上传异常: {str(e)}")
        return False, []


def upload_audio_to_api(file):
    """上传音频文件到 API"""
    if not file:
        return False, None

    # 文件大小限制 500MB
    MAX_SIZE = 500 * 1024 * 1024
    if file.size > MAX_SIZE:
        st.error(f"文件 {file.name} 超过大小限制 (500MB)")
        return False, None

    try:
        files_data = [("file", (file.name, file.getvalue(), file.type))]
        response = requests.post(
            f"{API_BASE_URL}/upload/audio",
            files=files_data,
            timeout=300,
        )

        if response.status_code == 200:
            data = response.json()
            file_id = data.get("file_ids")
            return True, file_id
        else:
            error_msg = response.json().get("detail", "上传失败")
            st.error(f"音频上传失败: {error_msg}")
            return False, None
    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务，请确保 FastAPI 服务已启动")
        return False, None
    except Exception as e:
        st.error(f"音频上传异常: {str(e)}")
        return False, None


def process_videos_api(video_ids, audio_id):
    """调用处理 API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/process",
            json={"video_ids": video_ids, "audio_id": audio_id},
            stream=True,
            timeout=600,
        )

        if response.status_code == 200:
            progress_bar = st.progress(0)
            status_text = st.empty()

            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        import json

                        data = json.loads(data_str)
                        status = data.get("status", "")
                        progress = data.get("progress", 0)
                        message = data.get("message", "")

                        progress_bar.progress(progress)
                        status_text.text(message)

                        if status == "completed":
                            return data.get("result_file_id")
                        elif status == "error":
                            st.error(f"处理失败: {message}")
                            return None

            return None
        else:
            error_msg = response.json().get("detail", "处理失败")
            st.error(f"视频处理失败: {error_msg}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务，请确保 FastAPI 服务已启动")
        return None
    except Exception as e:
        st.error(f"视频处理异常: {str(e)}")
        return None


def download_file_api(file_id):
    """下载文件"""
    try:
        response = requests.get(f"{API_BASE_URL}/download/{file_id}", timeout=300)
        return response.content
    except Exception as e:
        st.error(f"下载失败: {str(e)}")
        return None


def cleanup_api():
    """清理临时文件"""
    try:
        requests.delete(f"{API_BASE_URL}/cleanup/", timeout=30)
    except Exception:
        pass


def reset_state():
    """重置状态"""
    st.session_state.video_ids = []
    st.session_state.audio_id = None
    st.session_state.audio_filename = None
    st.session_state.result_file_id = None
    st.session_state.processing = False
    st.session_state.video_filenames = []
    st.session_state.video_uploaded = False
    st.session_state.audio_uploaded = False
    cleanup_api()


def main():
    """主函数"""
    init_session_state()

    st.title("🎬 视频自动剪辑系统")
    st.markdown("---")

    # 步骤 1: 上传视频文件
    st.header("步骤1: 上传视频文件 (MP4)")

    col1, col2 = st.columns([3, 1])

    with col1:
        video_files = st.file_uploader(
            "选择多个 MP4 视频文件",
            type=["mp4"],
            accept_multiple_files=True,
            key="video_uploader",
            disabled=st.session_state.processing,
        )

    with col2:
        st.write("")  # spacing
        st.write("")  # spacing
        upload_video_btn = st.button(
            "上传视频",
            key="upload_videos_btn",
            disabled=st.session_state.processing or not video_files or st.session_state.video_uploaded,
        )

    if upload_video_btn and video_files:
        with st.spinner("上传视频中..."):
            success, file_ids = upload_videos_to_api(video_files)
            if success and file_ids:
                st.session_state.video_ids = file_ids
                st.session_state.video_filenames = [f.name for f in video_files]
                st.session_state.video_uploaded = True
                st.success(f"成功上传 {len(file_ids)} 个视频文件")

    # 显示已上传的视频
    if st.session_state.video_ids:
        st.success(f"已上传 {len(st.session_state.video_ids)} 个视频文件:")
        for i, fname in enumerate(st.session_state.video_filenames):
            st.text(f"  {i + 1}. {fname}")

    st.markdown("---")

    # 步骤 2: 上传音频文件
    st.header("步骤2: 上传音频文件 (MP3/WAV)")

    col1, col2 = st.columns([3, 1])

    with col1:
        audio_file = st.file_uploader(
            "选择单个 MP3 或 WAV 音频文件",
            type=["mp3", "wav"],
            accept_multiple_files=False,
            key="audio_uploader",
            disabled=st.session_state.processing,
        )

    with col2:
        st.write("")  # spacing
        st.write("")  # spacing
        upload_audio_btn = st.button(
            "上传音频",
            key="upload_audio_btn",
            disabled=st.session_state.processing or not audio_file or st.session_state.audio_uploaded,
        )

    if upload_audio_btn and audio_file:
        with st.spinner("上传音频中..."):
            success, file_id = upload_audio_to_api(audio_file)
            if success and file_id:
                st.session_state.audio_id = file_id
                st.session_state.audio_filename = audio_file.name
                st.session_state.audio_uploaded = True
                st.success("成功上传音频文件")

    # 显示已上传的音频
    if st.session_state.audio_filename:
        st.success(f"已上传音频: {st.session_state.audio_filename}")

    st.markdown("---")

    # 步骤 3: 开始处理
    st.header("步骤3: 开始处理")

    col1, col2 = st.columns([1, 1])

    # 检查是否可以开始处理
    can_start = (
        st.session_state.video_ids
        and st.session_state.audio_id
        and not st.session_state.processing
    )

    with col1:
        start_button = st.button(
            "开始剪辑",
            key="start_process_btn",
            disabled=not can_start,
        )

    with col2:
        reset_button = st.button("清空重置", key="reset_btn")

    if reset_button:
        reset_state()
        st.rerun()

    if start_button and can_start:
        st.session_state.processing = True
        st.session_state.result_file_id = None

        with st.spinner("处理中，请稍候..."):
            result_id = process_videos_api(
                st.session_state.video_ids,
                st.session_state.audio_id,
            )
            st.session_state.result_file_id = result_id

        st.session_state.processing = False

        if result_id:
            st.success("处理完成！可以下载最终视频了。")

    st.markdown("---")

    # 步骤 4: 下载结果
    st.header("步骤4: 下载结果")

    if st.session_state.result_file_id:
        file_content = download_file_api(st.session_state.result_file_id)

        if file_content:
            st.download_button(
                label="📥 下载合成视频",
                data=file_content,
                file_name="final_video.mp4",
                mime="video/mp4",
                key="download_btn",
            )
            st.info("文件已准备就绪，点击上方按钮下载。")
    else:
        if st.session_state.processing:
            st.info("处理中，请稍候...")
        else:
            st.info("请先上传视频和音频文件，然后点击「开始剪辑」")

    # 底部信息
    st.markdown("---")
    st.caption("视频自动剪辑系统 | 基于 FastAPI + Streamlit")


if __name__ == "__main__":
    main()

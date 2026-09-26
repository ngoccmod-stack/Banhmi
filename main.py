import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

BASE = Path(__file__).resolve().parent
DOWNLOADS = BASE / "downloads"
DOWNLOADS.mkdir(exist_ok=True)

app = FastAPI(title="Bánh mì Video API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "youtu.be",
    "tiktok.com", "www.tiktok.com",
    "facebook.com", "www.facebook.com", "fb.watch",
    "x.com", "www.x.com", "twitter.com", "www.twitter.com",
    "threads.net", "www.threads.net",
}

class AnalyzeRequest(BaseModel):
    url: HttpUrl

class DownloadRequest(BaseModel):
    url: HttpUrl
    quality: str = "720"

def host_allowed(url: str) -> bool:
    m = re.match(r"^https?://([^/]+)", url.lower())
    if not m:
        return False
    host = m.group(1).split(":")[0]
    return host in ALLOWED_HOSTS or any(host.endswith("." + h) for h in ALLOWED_HOSTS)

def safe_filename(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|\r\n]+', "_", value or "video")
    value = value.strip(" ._")
    return (value[:100] or "video")

def run_ytdlp(url: str, extra: list[str], timeout: int = 300):
    cmd = ["yt-dlp", "--no-playlist", "--no-warnings", *extra, url]
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)

def cleanup_dir(path: Path):
    shutil.rmtree(path, ignore_errors=True)

@app.get("/")
def root():
    return {"service": "banhmivideo-api", "ok": True, "health": "/api/health"}

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "yt_dlp": shutil.which("yt-dlp") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
    }

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    url = str(req.url)
    if not host_allowed(url):
        raise HTTPException(400, "Nền tảng này chưa được bật trong V1.")

    try:
        p = run_ytdlp(url, ["--dump-single-json", "--skip-download"])
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Phân tích quá lâu và đã bị dừng.")

    if p.returncode != 0:
        raise HTTPException(
            400,
            "Không lấy được thông tin video. Video có thể riêng tư hoặc nền tảng đang chặn truy cập."
        )

    try:
        info = json.loads(p.stdout)
    except Exception:
        raise HTTPException(502, "Dữ liệu từ yt-dlp không hợp lệ.")

    heights = sorted(
        {
            int(f["height"])
            for f in info.get("formats", [])
            if f.get("vcodec") != "none" and f.get("height")
        },
        reverse=True,
    )

    return {
        "id": info.get("id"),
        "title": info.get("title") or "Video",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "platform": info.get("extractor_key") or info.get("extractor") or "Video",
        "qualities": heights[:12],
    }

@app.post("/api/download")
def download(req: DownloadRequest, background_tasks: BackgroundTasks):
    url = str(req.url)
    if not host_allowed(url):
        raise HTTPException(400, "Nền tảng này chưa được bật trong V1.")

    quality = str(req.quality)
    if quality not in {"360", "480", "720", "1080"}:
        quality = "720"

    job = uuid.uuid4().hex
    work = DOWNLOADS / job
    work.mkdir(parents=True, exist_ok=True)

    output = work / "%(title).80s [%(id)s].%(ext)s"
    fmt = f"bv*[height<={quality}]+ba/b[height<={quality}]/b"

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--restrict-filenames",
        "--recode-video", "mp4",
        "-f", fmt,
        "-o", str(output),
        url,
    ]

    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        cleanup_dir(work)
        raise HTTPException(504, "Tải video quá lâu và đã bị dừng.")

    if p.returncode != 0:
        cleanup_dir(work)
        raise HTTPException(400, "Không tải được video. Hãy thử video công khai khác.")

    mp4s = list(work.glob("*.mp4"))
    if not mp4s:
        cleanup_dir(work)
        raise HTTPException(500, "Không tìm thấy MP4 sau khi xử lý.")

    file = mp4s[0]
    download_name = safe_filename(file.stem) + ".mp4"

    # Xóa thư mục tạm sau khi FileResponse hoàn tất gửi file.
    background_tasks.add_task(cleanup_dir, work)

    return FileResponse(
        file,
        media_type="video/mp4",
        filename=download_name,
        background=background_tasks,
    )

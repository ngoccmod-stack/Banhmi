BÁNH MÌ VIDEO — BACKEND V3

Mục tiêu: giữ API cũ nhưng thêm BgUtils PO Token Provider để yt-dlp có thể xử lý tốt hơn các yêu cầu YouTube từ IP cloud.

Các file phải nằm ở ROOT của GitHub repo:
- Dockerfile
- start.sh
- main.py
- requirements.txt
- render.yaml

Render sẽ tự build lại sau khi push commit mới.

Sau khi deploy, mở:
https://banhmi-1nqh.onrender.com/api/health

Kết quả mong đợi:
{
  "ok": true,
  "version": "3.0.0",
  "yt_dlp": true,
  "ffmpeg": true,
  "deno": true,
  "pot_provider": true
}

Lưu ý: PO token không đảm bảo mọi video/IP đều vượt được mọi kiểm tra của YouTube. Nếu YouTube thay đổi cơ chế, backend có thể lại cần cập nhật.

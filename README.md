# Local WebDrop (iPhone <-> Arch Linux)

Mini web service lokal zero-dependency (menggunakan Python 3 standar) untuk transfer berkas dan sinkronisasi clipboard dua arah antara Arch Linux dan iPhone (Safari / iOS PWA) tanpa perlu koneksi internet luar atau aplikasi pihak ketiga.

## Fitur Utama
- **Zero External Dependencies**: Berjalan murni dengan pustaka standar Python 3 (`http.server`, `socketserver`, `json`).
- **QR Code Terminal**: Otomatis mendeteksi IP lokal (`192.168.x.x`) dan mencetak QR Code terminal via `qrencode` saat dijalankan. Cukup buka Kamera iPhone dan tap link.
- **Two-Way Clipboard**: Kirim teks/link dari iPhone langsung ke Linux (dan otomatis push ke Wayland/X11 clipboard via `wl-copy` / `xclip` jika ada) dan sebaliknya.
- **File Transfer**: Unggah foto, video, dokumen tanpa kompresi dengan progress bar dan drag-and-drop.
- **iOS Optimized UI**: 
  - Input font size 16px (mencegah auto-zoom Safari di iOS).
  - Dark mode glassmorphism + Dynamic Island capsule toast.
  - Safe-area inset support (`viewport-fit=cover`) untuk iPhone berponi / Dynamic Island.

## Cara Menjalankan

### Fish Shell / Bash
```fish
cd /home/kiiyuu/Projects/project-web/local-webdrop
python3 server.py
```

Bisa tentukan custom port jika diperlukan:
```fish
python3 server.py 8080
```

Berkas yang diunggah akan otomatis masuk ke folder:
`/home/kiiyuu/Projects/project-web/local-webdrop/uploads/`

# 🤖 Warungio WhatsApp Chatbot

Asisten Virtual Warungio — Chatbot WhatsApp resmi untuk platform Warungio, dibangun menggunakan [@whiskeysockets/baileys](https://github.com/WhiskeySockets/Baileys) dan didukung oleh Google Gemini AI.

## ✨ Fitur

- **AI-Powered**: Menggunakan Google Gemini API untuk menjawab pertanyaan secara cerdas dan natural.
- **Fallback Cerdas**: Saat AI nonaktif atau gagal, bot tetap bisa menjawab pertanyaan umum menggunakan asisten lokal.
- **Riwayat Percakapan**: Menyimpan konteks percakapan per nomor untuk pengalaman yang lebih personal.
- **Pemberitahuan Sekali**: Hanya mengirim pesan pengembangan satu kali per sesi.
- **Auto Reconnect**: Terhubung kembali secara otomatis saat koneksi terputus.
- **Modular**: Kode terstruktur rapi, mudah dikembangkan, dan mudah dipelihara.
- **Error Handling**: Tidak crash saat Gemini gagal, koneksi terputus, atau file rusak.

## 📁 Struktur Proyek

```
whatsapp-bot/
├── src/
│   ├── index.js           # Entry point — koneksi Baileys, QR, reconnect
│   ├── handler.js          # Pemrosesan pesan, AI, fallback
│   ├── history.js          # Manajemen riwayat percakapan
│   ├── config.js           # Konfigurasi dari .env
│   ├── ai/
│   │   └── gemini.js       # Wrapper Google Gemini API
│   ├── services/
│   │   └── whatsapp.js     # Helper pengiriman pesan
│   └── utils/
│       ├── logger.js       # Pino logger dengan pretty print
│       └── delay.js        # Utility sleep & backoff
├── data/
│   └── history.json        # Riwayat percakapan (auto-generated)
├── session/                # Session WhatsApp (QR login)
├── .env                    # Konfigurasi environment
├── .gitignore
├── package.json
└── README.md
```

## 🚀 Instalasi

### Prasyarat

- **Node.js v22+** (direkomendasikan v22 LTS)
- **npm** (bundled dengan Node.js)

### Langkah-langkah

```bash
# 1. Masuk ke direktori proyek
cd whatsapp-bot

# 2. Install dependencies
npm install

# 3. Konfigurasi environment
cp .env .env.local
# Edit .env — isi GEMINI_API_KEY dengan API key dari Google AI Studio
```

### Mendapatkan Gemini API Key

1. Buka [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Klik **"Get API Key"**
3. Buat API key baru
4. Salin API key ke `.env`:

```
GEMINI_API_KEY=AIzaSy...
```

## 🎯 Menjalankan Bot

```bash
# Jalankan bot
npm start

# Atau dengan file watching (auto restart saat ada perubahan)
npm run start:dev
```

### Scan QR Code

1. Jalankan `npm start`
2. QR Code akan muncul di terminal
3. Buka **WhatsApp** di ponsel
4. Tap **⋮** (tiga titik) > **Perangkat Tertaut** > **Tautkan Perangkat**
5. Scan QR Code yang muncul di terminal
6. Bot siap digunakan!

## ⚙️ Konfigurasi (.env)

| Variabel | Deskripsi | Default |
|----------|-----------|---------|
| `AI_ENABLED` | Aktifkan/nonaktifkan AI Gemini | `true` |
| `GEMINI_API_KEY` | API Key Google Gemini | (wajib diisi) |
| `GEMINI_MODEL` | Model Gemini yang digunakan | `gemini-2.0-flash` |
| `GEMINI_TEMPERATURE` | Kreativitas respons AI (0.0 - 1.0) | `0.7` |
| `GEMINI_MAX_TOKENS` | Panjang maksimal respons | `1024` |
| `RECONNECT_INTERVAL` | Interval reconnect (ms) | `5000` |
| `LOG_LEVEL` | Level logging: `info`, `debug`, `warn`, `error` | `info` |

## 🧹 Perintah Berguna

```bash
# Hapus session (untuk scan QR ulang)
npm run clear-session

# Mode development (auto restart saat ada perubahan file)
npm run start:dev
```

## 🔒 Keamanan

- Jangan commit `.env` ke repository — sudah diabaikan oleh `.gitignore`
- File session (`session/*.json`) berisi data autentikasi — jangan dibagikan
- `data/history.json` berisi riwayat percakapan — hapus secara berkala jika diperlukan

## 🏗️ Arsitektur

```
index.js ──→ handler.js ──→ ai/gemini.js ──→ Google Gemini API
              │                  │
              │                  └── history.js (konteks percakapan)
              │
              └── services/whatsapp.js (kirim pesan)
```

## 📄 Lisensi

MIT — Gunakan dengan bebas untuk keperluan pribadi maupun komersial.

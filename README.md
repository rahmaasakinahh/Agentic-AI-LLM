# **Agentic AI: Evaluasi Multilingual LLM Tool Calling**

---

Penelitian kerja praktik (KP) mengenai kemampuan Large Language Models (LLM) dalam melakukan *function calling* pada tugas dan variasi bahasa lokal. Penelitian berfokus pada ketepatan pemilihan fungsi, prediksi argumen, serta ketahanan model terhadap perubahan bentuk instruksi.

## **Tujuan Penelitian**

---

- Mengevaluasi kemampuan *tool calling* LLM pada instruksi bahasa Inggris dan Indonesia.
- Menganalisis kesalahan pemilihan fungsi dan prediksi argumen.
- Menguji ketahanan model terhadap variasi bahasa lokal.
- Membandingkan performa model melalui evaluasi AST dan analisis statistik berpasangan.

## **Dataset**

---

Penelitian menggunakan [MASSIVE-Agents](https://aclanthology.org/2025.findings-emnlp.1099/) dengan 3.287 data dan katalog 55 fungsi.

- **Bahasa evaluasi:** Inggris (`en-US`) dan Indonesia (`id-ID`).
- **Preprocessing:** pemeriksaan struktur data, audit ground truth (GT), dan pembagian data berbasis grup untuk mengurangi risiko kebocoran data.
- **Variasi bahasa:** slang/informal, singkatan, typo, code-switching Indonesia–Inggris, dan Indonesia–Jawa.

Pengembangan metode dan eksperimen yang dilaporkan menggunakan development set. Test set tidak digunakan pada tahap eksplorasi tersebut.

## **Model yang Dievaluasi**

---

| Model | Peran |
| --- | --- |
| Qwen2.5-7B-Instruct | Baseline |
| Gemma 2 9B Instruct | Baseline |
| Sahabat-AI v1 9B Instruct | Baseline |
| LFM2.5-8B-A1B | Model tambahan |

## **Alur Penelitian**

---

1. Inspeksi dataset dan Exploratory Data Analysis (EDA).
2. Preprocessing, pembagian data, dan audit ground truth.
3. Seleksi model dan pengujian kompatibilitas tool calling.
4. Evaluasi baseline pada instruksi Inggris dan Indonesia.
5. Evaluasi ulang menggunakan BFCL AST serta analisis kesalahan fungsi dan argumen.
6. Validasi pasangan instruksi EN–ID.
7. Pengembangan dan audit variasi bahasa lokal hingga versi V5.
8. Pengujian eksploratif ketahanan model terhadap variasi bahasa.
9. Analisis pasca-audit dan statistik berpasangan.

## **Metode Evaluasi**

---

- **BFCL AST Accuracy:** metrik utama untuk memeriksa kecocokan fungsi dan argumen menggunakan AST checker dari `bfcl-eval`.
- **Internal Exact Match:** metrik tambahan untuk membandingkan prediksi dengan ground truth.
- **Error Analysis:** identifikasi kesalahan fungsi, argumen, dan potensi ambiguitas anotasi.
- **McNemar Test:** pengujian perbedaan hasil benar/salah pada data berpasangan.

Skor BFCL AST pada penelitian ini bukan skor leaderboard resmi BFCL.

## **Progres Penelitian**

---

- Pemeriksaan otomatis dataset memisahkan 10 dari 3.287 data untuk review manual.
- Pengembangan variasi bahasa V5 mempertahankan 971 kandidat yang dapat ditelusuri dari versi sebelumnya.
- Eksperimen eksploratif Batch 80 membandingkan instruksi asli dan variasi bahasa pada empat model.
- Analisis sensitivitas dilakukan pada subset 70 variasi yang tidak ditahan oleh audit berbantuan AI.

Hasil tersebut masih bersifat eksploratif. Validasi semantik oleh manusia dan evaluasi akhir masih diperlukan sebelum menarik kesimpulan final.

## **Tools dan Teknologi**

---

Python, Jupyter Notebook, Ollama, MASSIVE-Agents, BFCL (`bfcl-eval`), dan analisis statistik McNemar.

## **Struktur Repository**

---

```text
Agentic-AI-LLM/
├── notebooks/
├── apply_manual_review.py
├── check_parallel_gt.py
├── requirements.txt
├── requirements-bfcl.txt
├── .gitignore
└── README.md
```

| File / Folder | Keterangan |
| --- | --- |
| `notebooks/` | Inspeksi data, preprocessing, evaluasi model, audit, pengembangan variasi bahasa, dan analisis statistik |
| `apply_manual_review.py` | Penerapan hasil review manual |
| `check_parallel_gt.py` | Pemeriksaan ground truth pada data paralel |
| `requirements.txt` | Dependensi utama penelitian |
| `requirements-bfcl.txt` | Dependensi evaluasi BFCL |

## **Notes**

---

- Penelitian masih berlangsung (*research in progress*).
- Dataset mentah, dataset hasil preprocessing, file model, dan hasil eksperimen terperinci tidak disertakan dalam repository.
- Notebook mendokumentasikan tahapan penelitian, tetapi tidak seluruh eksperimen dapat dijalankan ulang hanya dengan file yang tersedia di repository.
- Tidak ada pelatihan ulang model pada eksperimen ketahanan bahasa V5.
- Hasil penelitian dapat diperbarui setelah proses verifikasi dan validasi selesai.

## **Referensi**

---

- [MASSIVE-Agents — Findings of EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.1099/)
- [Berkeley Function Calling Leaderboard (BFCL)](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard)

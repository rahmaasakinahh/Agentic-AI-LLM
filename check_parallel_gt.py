"""Audit kesetaraan STRUKTURAL ground truth pada pasangan test EN–ID.

Jalankan dari root proyek KP-Agentic-AI:
    python check_parallel_gt.py

Input  : data/processed/massive_agents_reviewed/{en-US,id-ID}_test.jsonl
Output : results/parallel_subset/parallel_gt_check.csv
         results/parallel_subset/parallel_gt_summary.json

Perhatian: perbedaan nilai argument BUKAN bukti salah.
Jangan edit GT atau memutuskan validitas semantik dari hitungan exact-match ini.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed" / "massive_agents_reviewed"
OUT_DIR = ROOT / "results" / "parallel_subset"


def load_test(locale: str) -> dict[str, dict]:
    path = DATA_DIR / f"{locale}_test.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"Tidak ditemukan: {path}")
    by_id: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("language_code") != locale or record.get("split") != "test":
                raise ValueError(f"Locale/split tidak sesuai: {path.name} baris {i}")
            record_id = str(record["source_record_id"])
            if record_id in by_id:
                raise ValueError(f"record_id ganda dalam {locale}: {record_id}")
            if not isinstance(record.get("gt"), dict):
                raise ValueError(f"GT bukan objek pada {locale} ID {record_id}")
            by_id[record_id] = record
    return by_id


def arg_structure(gt: dict) -> set[tuple[str, str]]:
    result = set()
    for function, params in gt.items():
        if not isinstance(params, dict):
            raise ValueError(f"GT untuk fungsi {function!r} bukan objek")
        result.update((str(function), str(arg)) for arg in params)
    return result


def list_value_differences(gt_en: dict, gt_id: dict) -> list[str]:
    diffs = []
    for func in sorted(gt_en):
        for arg in sorted(gt_en[func]):
            if gt_en[func][arg] != gt_id[func][arg]:
                diffs.append(f"{func}.{arg}")
    return diffs


def main() -> None:
    en = load_test("en-US")
    ind = load_test("id-ID")
    shared = sorted(en.keys() & ind.keys(), key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))
    if not shared:
        raise ValueError("Tidak ditemukan pasangan dengan ID sama pada test EN dan ID")
    if len(shared) != 933:
        raise ValueError(f"Pasangan ditemukan {len(shared)}, berbeda dari hasil terminal sebelumnya: 933. Periksa file input.")

    rows = []
    count = Counter()
    for record_id in shared:
        a, b = en[record_id], ind[record_id]
        group_match = a["group_id"] == b["group_id"]
        functions_match = set(a["gt"]) == set(b["gt"])
        structure_match = arg_structure(a["gt"]) == arg_structure(b["gt"])
        values_different = []
        if not group_match:
            status = "GROUP_MISMATCH"
        elif not functions_match:
            status = "FUNCTION_MISMATCH"
        elif not structure_match:
            status = "ARGUMENT_KEY_MISMATCH"
        else:
            values_different = list_value_differences(a["gt"], b["gt"])
            status = "VALUE_DIFFERENCE_REVIEW" if values_different else "EXACT_GT"
        count[status] += 1
        rows.append({
            "record_id": record_id,
            "group_id": a["group_id"],
            "en_row_key": a["row_key"],
            "id_row_key": b["row_key"],
            "target_functions": ";".join(sorted(a["gt"])),
            "status": status,
            "different_value_fields": ";".join(values_different),
            "en_question": a["question"],
            "id_question": b["question"],
            "en_gt_json": json.dumps(a["gt"], ensure_ascii=False, sort_keys=True),
            "id_gt_json": json.dumps(b["gt"], ensure_ascii=False, sort_keys=True),
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "parallel_gt_check.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "source": "MASSIVE-Agents, reviewed TEST EN–ID",
        "en_test_records": len(en),
        "id_test_records": len(ind),
        "paired_ids": len(shared),
        "status_counts": {name: count[name] for name in (
            "EXACT_GT", "VALUE_DIFFERENCE_REVIEW", "ARGUMENT_KEY_MISMATCH",
            "FUNCTION_MISMATCH", "GROUP_MISMATCH")},
        "note": "EXACT_GT berarti cocok secara struktural dan tekstual. VALUE_DIFFERENCE_REVIEW tidak otomatis salah; perlu review kesetaraan makna. Belum menjadi subset paralel tervalidasi.",
    }
    (OUT_DIR / "parallel_gt_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== VALIDASI AWAL GT PARALEL EN-ID ===")
    print("Test EN:", len(en), "| Test ID:", len(ind))
    print("Pasangan test:", len(shared))
    for name in ("EXACT_GT", "VALUE_DIFFERENCE_REVIEW", "ARGUMENT_KEY_MISMATCH", "FUNCTION_MISMATCH", "GROUP_MISMATCH"):
        print(f"{name}: {count[name]}")
    print("Laporan:", OUT_DIR)
    print("Belum ada perubahan pada dataset maupun GT asli.")


if __name__ == "__main__":
    main()

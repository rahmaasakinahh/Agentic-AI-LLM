"""Terapkan hasil review manual MASSIVE-Agents tanpa menimpa dataset asli.

Jalankan dari root proyek: python apply_manual_review.py
Input: results/preprocessing/manual_resolution_step3_all_reviewed.csv
       data/processed/massive_agents/{en-US,id-ID}_{development,test}.jsonl
       data/processed/massive_agents/review_required.jsonl
Output: data/processed/massive_agents_reviewed/
        results/preprocessing_reviewed/

CATATAN: status hasil audit mengikuti keputusan dalam CSV, yang masih perlu
verifikasi metodologis sebelum digunakan sebagai set evaluasi definitif.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

LANGUAGES = ("en-US", "id-ID")
SPLITS = ("development", "test")
REVIEW_FILENAME = "manual_resolution_step3_all_reviewed.csv"


def find_root() -> Path:
    here = Path(__file__).resolve().parent
    for root in (here, *here.parents):
        if (root / "data/processed/massive_agents/review_required.jsonl").is_file():
            return root
    raise FileNotFoundError(
        "Folder data/processed/massive_agents/review_required.jsonl tidak ditemukan. "
        "Letakkan skrip di root proyek KP lalu jalankan lagi."
    )


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"File belum ada: {path}")
    items = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for number, line in enumerate(fh, 1):
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ValueError(f"JSON rusak: {path.name} baris {number}: {error}") from error
    return items


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    root = find_root()
    source_dir = root / "data/processed/massive_agents"
    audit_file = root / "results/preprocessing" / REVIEW_FILENAME
    output_dir = root / "data/processed/massive_agents_reviewed"
    report_dir = root / "results/preprocessing_reviewed"

    if not audit_file.is_file():
        raise FileNotFoundError(
            f"Keputusan audit tidak ditemukan: {audit_file}\n"
            "Salin manual_resolution_step3_all_reviewed.csv ke folder results/preprocessing."
        )

    with audit_file.open("r", encoding="utf-8-sig", newline="") as fh:
        audit_rows = list(csv.DictReader(fh))
    required = {"row_key", "language_code", "record_id", "group_id", "planned_split", "question", "gt_json", "review_decision", "decision_reason"}
    if not audit_rows or not required.issubset(audit_rows[0]):
        raise ValueError("Kolom CSV audit tidak lengkap.")
    audits = {}
    for audit in audit_rows:
        key = audit["row_key"].strip()
        decision = audit["review_decision"].strip().lower()
        if key in audits:
            raise ValueError(f"row_key ganda dalam CSV audit: {key}")
        if decision not in {"keep", "exclude"}:
            raise ValueError(f"Keputusan untuk {key} tidak valid: {decision!r}. Gunakan keep/exclude.")
        if not audit["decision_reason"].strip():
            raise ValueError(f"Alasan audit untuk {key} masih kosong.")
        if audit.get("corrected_gt_json", "").strip():
            raise ValueError(f"{key}: skrip ini belum mendukung koreksi GT. Audit manual dulu.")
        audits[key] = audit

    # Periksa bahwa dua bahasa dengan record_id sama menerima keputusan seragam.
    decisions_by_id = defaultdict(set)
    for audit in audit_rows:
        decisions_by_id[audit["record_id"]].add(audit["review_decision"].strip().lower())
    if any(len(v) != 1 for v in decisions_by_id.values()):
        raise ValueError("Terdapat keputusan berbeda pada record_id yang sama antarbahasa.")

    source_files = {(lang, split): source_dir / f"{lang}_{split}.jsonl"
                    for lang in LANGUAGES for split in SPLITS}
    existing = {}
    all_rows = {}
    for (lang, split), path in source_files.items():
        entries = read_jsonl(path)
        existing[(lang, split)] = entries
        for row in entries:
            key = row["row_key"]
            if key in all_rows:
                raise ValueError(f"row_key duplikat di input: {key}")
            if row["language_code"] != lang or row["split"] != split:
                raise ValueError(f"Bahasa atau split tidak cocok di {key}")
            all_rows[key] = row

    review_rows = read_jsonl(source_dir / "review_required.jsonl")
    if set(audits) != {row["row_key"] for row in review_rows}:
        missing = {row["row_key"] for row in review_rows} - set(audits)
        extra = set(audits) - {row["row_key"] for row in review_rows}
        raise ValueError(f"Audit dan review_required.jsonl tidak cocok. Belum diaudit: {sorted(missing)}; ekstra: {sorted(extra)}")

    output = {(lang, split): [dict(row, review_status="eligible_after_review") for row in entries]
              for (lang, split), entries in existing.items()}
    excluded = []
    for source_row in review_rows:
        key = source_row["row_key"]
        audit = audits[key]
        for name, a, b in (
            ("language_code", source_row["language_code"], audit["language_code"]),
            ("record_id", str(source_row["source_record_id"]), audit["record_id"]),
            ("group_id", source_row["group_id"], audit["group_id"]),
            ("split", source_row["split"], audit["planned_split"]),
            ("question", source_row["question"], audit["question"]),
        ):
            if str(a) != str(b):
                raise ValueError(f"Audit {key}, kolom {name} berbeda dari sumber.")
        if source_row["gt"] != json.loads(audit["gt_json"]):
            raise ValueError(f"GT {key} berubah dari sumber. Proses dihentikan.")
        if key in all_rows:
            raise ValueError(f"Review row {key} sudah ada dalam eligible provisional.")
        all_rows[key] = source_row
        decision = audit["review_decision"].strip().lower()
        if decision == "keep":
            output[(source_row["language_code"], source_row["split"])].append(
                dict(source_row, review_status="eligible_after_manual_review")
            )
        else:
            excluded.append(dict(source_row, review_status="excluded_after_manual_review"))

    final_included = [row for entries in output.values() for row in entries]
    total = len(final_included) + len(excluded)
    if total != len(all_rows) or len({r["row_key"] for r in final_included + excluded}) != total:
        raise AssertionError("Ada record yang hilang atau muncul lebih dari satu kali.")

    # Cegah leakage grup dan ID antar-development/test, termasuk record yang ditahan.
    split_by_group = defaultdict(set)
    split_by_record_id = defaultdict(set)
    for row in final_included:
        split_by_group[row["group_id"]].add(row["split"])
        split_by_record_id[str(row["source_record_id"])].add(row["split"])
    if any(len(s) > 1 for s in split_by_group.values()):
        raise AssertionError("DATA LEAKAGE: group_id ditemukan di development sekaligus test.")
    if any(len(s) > 1 for s in split_by_record_id.values()):
        raise AssertionError("DATA LEAKAGE: record_id ditemukan di development sekaligus test.")

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    for (lang, split), rows in output.items():
        # Pertahankan urutan baris berdasarkan nomor record dari sumber.
        rows.sort(key=lambda r: int(r["row_key"].split(":")[1]))
        write_jsonl(output_dir / f"{lang}_{split}.jsonl", rows)
    write_jsonl(output_dir / "excluded_after_review.jsonl", excluded)

    manifest_cols = ["row_key", "record_id", "language_code", "question", "target_function",
                     "group_id", "split", "review_status", "review_decision"]
    with (report_dir / "split_manifest_reviewed.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=manifest_cols)
        writer.writeheader()
        for row in sorted(final_included + excluded, key=lambda r: r["row_key"]):
            key = row["row_key"]
            writer.writerow({
                "row_key": key,
                "record_id": row["source_record_id"],
                "language_code": row["language_code"],
                "question": row["question"],
                "target_function": ";".join(sorted(row["gt"].keys())),
                "group_id": row["group_id"],
                "split": row["split"],
                "review_status": row["review_status"],
                "review_decision": audits[key]["review_decision"].strip().lower() if key in audits else "not_required",
            })

    counts = {f"{lang}_{split}": len(output[(lang, split)]) for lang in LANGUAGES for split in SPLITS}
    summary = {
        "source_total": len(all_rows),
        "eligible_original": sum(len(v) for v in existing.values()),
        "manual_review_total": len(review_rows),
        "manual_keep": sum(a["review_decision"].strip().lower() == "keep" for a in audit_rows),
        "manual_exclude": len(excluded),
        "ready_to_evaluate_candidate": len(final_included),
        "development": sum(len(output[(lang, "development")]) for lang in LANGUAGES),
        "test": sum(len(output[(lang, "test")]) for lang in LANGUAGES),
        "counts_by_file": counts,
        "anti_leakage_group_and_id": "PASS",
        "gt_modified": False,
        "original_preprocessing_files_overwritten": False,
        "audit_file": str(audit_file.relative_to(root)),
        "audit_status": "provisional decisions; methodological/source verification still required",
    }
    (report_dir / "finalization_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\n=== VALIDASI HASIL REVIEW: LULUS ===")
    for name, count in counts.items():
        print(f"{name}: {count}")
    print("Total siap evaluasi (sementara):", len(final_included))
    print("Total exclude:", len(excluded))
    print("Anti-leakage group_id dan record_id: LULUS")
    print("Data asli tidak ditimpa.\nOutput:", output_dir, "\nLaporan:", report_dir)


if __name__ == "__main__":
    main()

"""data/samples/*.{jsonl,csv} → Flyway repeatable seed SQL 변환.

산출물: apps/serving/src/main/resources/db/seed/R__seed_sample_data.sql
- events_raw 1000건 + item + user_profile (전부 ON CONFLICT DO NOTHING → 멱등)
- seed 프로파일에서만 Flyway locations에 포함된다 (application.yml 참조)
- 샘플 재생성(generate.py) 후 이 스크립트를 다시 돌리면 SQL도 갱신됨
"""
import csv
import json
from pathlib import Path

SAMPLES = Path(__file__).parent
OUT = SAMPLES / "../../apps/serving/src/main/resources/db/seed/R__seed_sample_data.sql"


def q(v) -> str:
    """SQL 리터럴 (None/'' → NULL, 문자열은 '' 이스케이프)."""
    if v is None or v == "":
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


lines = [
    "-- 합성 샘플 데이터 시드 (generate.py → to_seed_sql.py 산출물, 수동 편집 금지)",
    "-- repeatable 마이그레이션: 체크섬 변경 시에만 재실행, ON CONFLICT로 멱등",
    "",
]

# ── events_raw (bronze) ──────────────────────────────────────────────────────
rows = []
for line in (SAMPLES / "events.sample.jsonl").open():
    e = json.loads(line)
    payload = json.dumps(e, ensure_ascii=False).replace("'", "''")
    rows.append(
        f"({q(e['eventId'])}, {q(e['eventType'])}, {q(e['userId'])}, {q(e['itemId'])}, "
        f"{q(e['sessionId'])}, {q(e.get('position'))}, {q(e['consent'])}, {q(e['ts'])}, '{payload}'::jsonb)"
    )
lines += [
    "INSERT INTO events_raw (event_id, event_type, user_id, item_id, session_id, position, consent, event_ts, payload)",
    "VALUES",
    ",\n".join(rows),
    "ON CONFLICT (event_id) DO NOTHING;",
    "",
]

# ── item ─────────────────────────────────────────────────────────────────────
rows = []
for r in csv.DictReader((SAMPLES / "items.sample.csv").open()):
    rows.append(
        f"({q(r['item_id'])}, {q(r['category'])}, {q(r['brand'])}, {int(r['price'])}, "
        f"{q(r['currency'])}, {q(r['status'])}, {q(r['created_at'])})"
    )
lines += [
    "INSERT INTO item (item_id, category, brand, price, currency, status_cd, create_date)",
    "VALUES",
    ",\n".join(rows),
    "ON CONFLICT (item_id) DO NOTHING;",
    "",
]

# ── user_profile ─────────────────────────────────────────────────────────────
rows = []
for r in csv.DictReader((SAMPLES / "users.sample.csv").open()):
    birth = int(r["birth_year"]) if r["birth_year"] else "NULL"
    consent = "true" if r["consent"] == "True" else "false"
    rows.append(f"({q(r['user_id'])}, {q(r['gender'])}, {birth}, {q(r['joined_at'])}, {consent})")
lines += [
    "INSERT INTO user_profile (user_id, gender, birth_year, join_date, is_consent)",
    "VALUES",
    ",\n".join(rows),
    "ON CONFLICT (user_id) DO NOTHING;",
    "",
]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines))
print(f"{OUT.resolve()}: {OUT.stat().st_size // 1024}KB")

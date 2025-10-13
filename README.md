# 顧客・キャスト売上管理（FastAPI版）
## セットアップ
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# DB作成 & スキーマ適用（簡易）
python - <<'PY'
import sqlite3, pathlib
pathlib.Path('app').mkdir(exist_ok=True)
conn = sqlite3.connect('app/app.db')
conn.executescript(open('app/schema.sql','r',encoding='utf-8').read())
conn.commit(); conn.close()
print('DB ready')
PY

# 起動
uvicorn app.main:app --reload

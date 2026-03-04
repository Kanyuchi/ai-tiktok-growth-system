.PHONY: install postgres-up postgres-down setup-db run-daily dashboard auth-url check

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -e .

postgres-up:
	docker compose up -d postgres

postgres-down:
	docker compose down

setup-db:
	. .venv/bin/activate && python scripts/setup_db.py

run-daily:
	. .venv/bin/activate && python scripts/run_daily.py

dashboard:
	. .venv/bin/activate && streamlit run dashboard/app.py

auth-url:
	. .venv/bin/activate && python scripts/tiktok_cli.py auth-url

check:
	. .venv/bin/activate && python scripts/tiktok_cli.py check

.PHONY: run stop build test seed migrate clean

run:
	docker-compose up -d
	@echo "✅ PostgreSQL running on port 5432"

stop:
	docker-compose down

build:
	docker-compose up -d --build

test:
	pytest tests/ -v

seed:
	python scripts/seed.py

migrate:
	alembic upgrade head

clean:
	docker-compose down -v
	rm -rf __pycache__ */__pycache__

clean:
	docker-compose down -v
	@echo "⚠️  All data deleted"

psql:
	docker exec -it ab_postgres psql -U abtest_user -d abtest_db

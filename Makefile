.PHONY: run stop build test seed logs clean

run:
	docker-compose up -d
	@echo "✅ PostgreSQL running on port 5432"
	@echo "✅ Redis running on port 6379"

stop:
	docker-compose down

build:
	docker-compose up -d --build

logs:
	docker-compose logs -f

logs-db:
	docker-compose logs -f postgres

logs-app:
	tail -f logs/app.log

test:
	pytest tests/ -v

install:
	pip install -r requirements.txt

migrate:
	alembic upgrade head

seed:
	python scripts/seed.py

clean:
	docker-compose down -v
	@echo "⚠️  All data deleted"

psql:
	docker exec -it ab_postgres psql -U abtest_user -d abtest_db

redis-cli:
	docker exec -it ab_redis redis-cli

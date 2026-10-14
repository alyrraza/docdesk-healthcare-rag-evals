# Shortcuts for the Docker demo. The same commands are in the README for machines without make.
.PHONY: env up seed demo down

env:
	python scripts/make_env.py

up:
	docker compose up -d --build --wait

seed:
	docker compose exec api python scripts/demo_seed.py

demo:
	docker compose exec api python scripts/demo_retrieve.py "How does rubella show up in someone who gets symptoms?" --expect seed:medlineplus:medlineplus-387

down:
	docker compose down

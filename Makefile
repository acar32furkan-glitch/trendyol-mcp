.DEFAULT_GOAL := help
PY := uv run

help: ## Komutları listele
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

sync: ## Bağımlılıkları kur
	uv sync --all-extras --dev

lint: ## ruff ile lint
	$(PY) ruff check .

fmt: ## ruff ile biçimlendir
	$(PY) ruff format .
	$(PY) ruff check --fix .

type: ## mypy (strict)
	$(PY) mypy

test: ## testler
	$(PY) pytest

cov: ## kapsamlı test
	$(PY) pytest --cov=trendyol_mcp --cov-report=term-missing

check: lint type test ## Tüm kalite kapısı

demo: ## örnek veriyle günlük Türkçe özet
	$(PY) trendyol-mcp --source fixture demo

serve: ## MCP sunucusunu stdio üzerinden başlat
	$(PY) trendyol-mcp --source auto serve

demo-svg: ## README için SVG demo kaydını yenile
	$(PY) python scripts/make_demo_svg.py

clean: ## geçici dosyaları sil
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml

.PHONY: help sync lint fmt type test cov check demo serve demo-svg clean

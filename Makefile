SHELL := /bin/bash
API := apps/api
WEB := apps/web
VENV := $(API)/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install venv provision seed load reload dev api web verify local local-down clean

## Instala dependencias de API y Web
install: venv
	$(PIP) install -q -r $(API)/requirements.txt
	cd $(WEB) && npm install

venv:
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install -q --upgrade pip

## Crea el grupo de recursos y el contenedor Neo4j en Azure
provision:
	./infra/provision.sh

## Genera el grafo multidimensional, el corpus y el embebedor
seed: venv
	$(PY) scripts/seed.py

## Carga el grafo y el corpus en Neo4j
load: venv
	$(PY) scripts/load_neo4j.py

## Borra el grafo y lo reconstruye desde cero
reload: venv
	$(PY) scripts/load_neo4j.py --recrear

## Levanta API (8001) y Web (3001) en paralelo.
## Los puertos son distintos a los de la versión PostgreSQL para poder comparar
## las dos soluciones lado a lado.
dev:
	@$(MAKE) -j2 api web

api:
	cd $(API) && ../../$(VENV)/bin/uvicorn main:app --reload --port 8001

web:
	cd $(WEB) && npm run dev

## Corre la verificación de extremo a extremo y falla si algo no se alcanza
verify: venv
	$(PY) scripts/verify_kag.py

## Neo4j local en docker, sin nada de Azure
local:
	docker compose up -d neo4j
	@echo "Esperando a que Neo4j acepte conexiones…"
	@until docker compose exec -T neo4j cypher-shell -u neo4j -p atlas-local 'RETURN 1' >/dev/null 2>&1; do sleep 2; done
	@echo "Listo en bolt://localhost:7687 · navegador http://localhost:7474"

local-down:
	docker compose down -v

clean:
	rm -rf $(VENV) $(WEB)/node_modules $(WEB)/.next data/*.json data/*.npz data/*.vocab.json

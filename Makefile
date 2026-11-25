# Atajos. En Windows sin make: copiar el comando de cada objetivo.
PY ?= python
MODULO ?= enot/verificador.py
DT_CSV ?= data/datatourisme/datatourisme-reg-bfc.csv
SPLIT ?= dev
SISTEMAS ?= B0,B1,B2,enot

.PHONY: install check test lint mutation tests-modificados registro datatourisme extract eda eval

install:
	$(PY) -m pip install -r requirements.txt

lint:
	ruff check .

test:
	$(PY) -m pytest -q

# Sensor principal: tiene que pasar antes de abrir un PR (AGENTS.md)
check: lint test

# Mutation testing sobre un módulo: ¿los tests detectarían un error? (ADR-0008)
PATRON = $(subst /,.,$(basename $(MODULO)))
mutation:
	rm -rf mutants
	-mutmut run "$(PATRON)*" > /dev/null 2>&1
	@echo "Resultado para $(PATRON):"
	@mutmut results --all true 2>/dev/null | grep "$(PATRON)" | awk -F': ' '{print $$2}' | sort | uniq -c
	@echo "Sobrevivientes (revisar con: mutmut show <nombre>):"
	@mutmut results 2>/dev/null | grep "$(PATRON)" | grep survived || echo "  ninguno"

BASE ?= origin/desarrollo

# Lista tests que ya existían en la base y fueron modificados en esta rama
tests-modificados:
	$(PY) scripts/tests_modificados.py $(BASE)

# Registro obligatorio: entrada de CHANGELOG + ADR nuevo en la rama (ADR-0010)
registro:
	$(PY) scripts/registro_obligatorio.py $(BASE)

datatourisme:
	$(PY) -m corpus datatourisme $(DT_CSV)

extract:
	$(PY) -m corpus extract

eda:
	$(PY) -m corpus eda

# Benchmark (spec 007, ADR-0017): reports/eval_<split>_<fecha>.json. SISTEMAS=B1 corre sin claves.
eval:
	$(PY) -m eval.correr --split $(SPLIT) --sistemas $(SISTEMAS)

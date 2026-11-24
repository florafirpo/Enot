# Atajos. En Windows sin make: copiar el comando de cada objetivo.
PY ?= python
MODULO ?= enot/verificador.py
DT_CSV ?= data/datatourisme/datatourisme-reg-bfc.csv

.PHONY: install check test lint mutation tests-modificados datatourisme extract eda

install:
	$(PY) -m pip install -r requirements.txt

lint:
	ruff check .

test:
	$(PY) -m pytest -q

# Sensor principal: tiene que pasar antes de abrir un PR (AGENTS.md)
check: lint test

# Mutation testing sobre un módulo: ¿los tests detectarían un error? (ADR-0008)
mutation:
	mutmut run "$(subst /,.,$(basename $(MODULO)))*" ; mutmut results

# Lista tests que ya existían en main y fueron modificados en esta rama
tests-modificados:
	$(PY) scripts/tests_modificados.py

datatourisme:
	$(PY) -m corpus datatourisme $(DT_CSV)

extract:
	$(PY) -m corpus extract

eda:
	$(PY) -m corpus eda

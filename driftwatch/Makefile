.PHONY: demo test lint clean

demo:            ## fresh seeded world + UI on :8000
	rm -f driftwatch.db driftwatch.db-*
	python3 apps/engine/serve.py

test:            ## full suite (23 tests incl. E2E mirror-break)
	cd apps/engine && python3 -m unittest discover -s tests

lint:
	ruff check apps/engine

clean:
	rm -f driftwatch.db driftwatch.db-*

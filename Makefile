.PHONY: demo test lint clean

demo:            ## fresh seeded world + UI on :8000
	rm -f driftwatch.db driftwatch.db-*
	python3 backend/serve.py

test:            ## full suite (23 tests incl. E2E mirror-break)
	cd backend && python3 -m unittest discover -s tests

lint:
	ruff check backend

clean:
	rm -f driftwatch.db driftwatch.db-*

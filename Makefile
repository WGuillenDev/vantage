EXAMPLES := projects/contract/examples
OUTPUT   := projects/pipeline/output
STORAGE  := projects/frontend/public/storage

.PHONY: mock publish validate all osm worldpop imerg timecheck review-prepare review-summary

mock:
	test -d $(EXAMPLES)
	rm -rf $(STORAGE)
	mkdir -p $(STORAGE)
	cp -r $(EXAMPLES)/. $(STORAGE)/

publish:
	test -d $(OUTPUT)
	rm -rf $(STORAGE)
	mkdir -p $(STORAGE)
	cp -r $(OUTPUT)/. $(STORAGE)/

validate:
	uv run --project projects/pipeline validate $(STORAGE)

all:
	uv run --project projects/pipeline pipeline-run $(if $(AREA),--area $(AREA))

osm:
	uv run --project projects/pipeline road-graph --area $(AREA) --download

worldpop:
	uv run --project projects/pipeline population-data --area $(AREA) --download

imerg:
	uv run --project projects/pipeline rain-context --area $(AREA) --download

timecheck:
	uv run --project projects/pipeline timecheck --area $(AREA)

review-prepare:
	uv run --project projects/pipeline manual-review prepare --area $(AREA)

review-summary:
	uv run --project projects/pipeline manual-review summarize --area $(AREA)

EXAMPLES := projects/contract/examples
OUTPUT   := projects/pipeline/output
STORAGE  := projects/frontend/public/storage

.PHONY: mock publish validate all osm timecheck review-prepare review-summary

mock:
	rm -rf $(STORAGE)
	mkdir -p $(STORAGE)
	cp -r $(EXAMPLES)/. $(STORAGE)/

publish:
	rm -rf $(STORAGE)
	mkdir -p $(STORAGE)
	cp -r $(OUTPUT)/. $(STORAGE)/

validate:
	uv run --project projects/pipeline validate $(STORAGE)

all:
	@echo "all: not implemented yet"; exit 1

osm:
	uv run --project projects/pipeline road-graph --area $(AREA) --download

timecheck:
	uv run --project projects/pipeline timecheck --area $(AREA)

review-prepare:
	uv run --project projects/pipeline manual-review prepare --area $(AREA)

review-summary:
	uv run --project projects/pipeline manual-review summarize --area $(AREA)

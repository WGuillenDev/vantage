EXAMPLES := projects/contract/examples
OUTPUT   := projects/pipeline/output
STORAGE  := projects/frontend/public/storage

.PHONY: mock publish validate all

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

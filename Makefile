EXAMPLES := projects/contract/examples
STORAGE  := projects/frontend/public/storage

.PHONY: mock validate all

mock:
	rm -rf $(STORAGE)
	mkdir -p $(STORAGE)
	cp -r $(EXAMPLES)/. $(STORAGE)/

validate:
	uv run --project projects/pipeline validate $(STORAGE)

all:
	@echo "all: not implemented yet"; exit 1

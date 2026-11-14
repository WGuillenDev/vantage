EXAMPLES := projects/contract/examples
DATA     := projects/frontend/public/storage

.PHONY: mock validate all

mock:
	rm -rf $(DATA)
	mkdir -p $(DATA)
	cp -r $(EXAMPLES)/. $(DATA)/

validate:
	@echo "validate: not implemented yet"; exit 1

all:
	@echo "all: not implemented yet"; exit 1

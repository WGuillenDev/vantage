EXAMPLES := projects/contract/examples
DATA     := projects/frontend/public/data

.PHONY: mock validate all

mock:
	mkdir -p $(DATA)
	cp -r $(EXAMPLES)/. $(DATA)/

validate:
	@echo "validate: not implemented yet"; exit 1

all:
	@echo "all: not implemented yet"; exit 1

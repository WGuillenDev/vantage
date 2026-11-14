# Repo-level commands. Needs a POSIX shell (Git Bash) for cp/mkdir.
EXAMPLES := projects/contract/examples
DATA     := projects/frontend/public/data

.PHONY: mock validate all

# Copy the mock data into the folder the frontend reads.
mock:
	@test -d $(EXAMPLES) || { echo "No mocks yet: $(EXAMPLES) is missing (task B5)"; exit 1; }
	mkdir -p $(DATA)
	cp -r $(EXAMPLES)/. $(DATA)/

# Not implemented: fails on purpose so CI cannot pass without a real check (task B5).
validate:
	@echo "validate is not implemented yet (needs schemas, tasks B4/B5)"; exit 1

# Not implemented: fails on purpose until the pipeline exists (task P7).
all:
	@echo "all is not implemented yet (needs the pipeline, task P7)"; exit 1

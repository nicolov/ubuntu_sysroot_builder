.PHONY: docker-shell
docker-shell:
	docker-compose build \
	&& docker-compose run builder bash

example:
	clang-3.8 --sysroot=/src/root -lm -lpng -o example example.c

install:
	python -m pip install -r requirements.txt

test:
	black --check .
	mypy .
	python -m coverage run -m pytest
	python -m coverage report --omit="/usr/lib/*"
	python -m coverage html --omit="/usr/lib/*"

lint:
	black .
	mypy .

run: lint
	echo
	echo ================ RUN ==============
	python .

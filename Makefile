install:
	python -m pip install -r requirements.txt

test:
	black --check .
	mypy .
	coverage run -m pytest
	coverage report --omit="/usr/lib/*"
	coverage html --omit="/usr/lib/*"

lint:
	black .
	mypy .

run: lint test
	echo
	echo ================ RUN ==============
	python .

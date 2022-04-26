install:
	python -m pip install -r requirements.txt

test:
	flake8
	mypy .
	coverage run -m pytest
	coverage report --omit="/usr/lib/*"
	coverage html --omit="/usr/lib/*"

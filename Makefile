test:
	flake8
	mypy .
	coverage run -m pytest
	coverage html --omit="/usr/lib/*" && browse htmlcov/index.html
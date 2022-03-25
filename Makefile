test:
	flake8
	mypy .
	coverage run -m pytest
	coverage report --omit="/usr/lib/*"
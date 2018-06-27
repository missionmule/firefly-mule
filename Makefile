init:
	pip3 install -r requirements.txt

test:
	python3 setup.py test

run:
	python3 avionics

.PHONY: init test

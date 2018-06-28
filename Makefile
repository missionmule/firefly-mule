init:
	pip3 install -r requirements.txt

test:
	python3 setup.py nosetests --rednose

run:
	python3 avionics

.PHONY: init test

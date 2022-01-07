clean:
	rm -rf build dist *egg-info

build:
	python setup.py install
	python setup.py sdist bdist_wheel

build-publish: clean build publish

lint:
	cd tracker && autopep8 --in-place --recursive -a .

publish:
	python -m twine upload --repository testpypi dist/* 

release:
	# type = (major | minor | patch)
	bump2version $(type) tracker/__init__.py

requirements:
	pip install -r requirements_dev.txt
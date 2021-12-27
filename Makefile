include .env
export

clean:
	rm spreadsheets/$(OUTPUT_FILE_NAME)

run: clean
	python app.py
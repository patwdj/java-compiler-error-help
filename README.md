**Title**

This repository contains the following files:
- dataset.xlsm: Dataset and results used in study. Includes underlying Java codes, SO links, ChatGPT answers and annotations.
- rbo_calc.ipynb: Notebook to calculate rbo values and generate figures.
- num_calc.ipynb: Notebook to calculate median number of results.
- plugin code to get links: Sublime plugin to get links returned from StackExchange API and Google from the 72 different query combinations as described in the study. Can be run on your Java files. Follow README file within folder for set-up instructions. Tool is dependent on several libraries:
  - Tree-sitter to parse user code; more information available here: https://tree-sitter.github.io/tree-sitter/
  - Beautiful Soup to scrape information from web pages; more information available here: https://pypi.org/project/beautifulsoup4/
  - Python Requests library to send HTTP requests to Google; more information available here: https://pypi.org/project/requests/





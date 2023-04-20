Study: Title

Sublime plugin to get links returned from StackExchange API and Google from the 72 different query combinations as described in the study.

Along with this README the following are available:
1. "QueryEvaluationCommand.py" : A Sublime Text 4 plugin created for this research study. The plugin, once setup, can be called directly from the Sublime Text 4 console and will automatically log results as required. Results will saved under result_logger.log file
2. "tree-sitter" file folder: A build of the tree-sitter library that is version compatible with the Sublime Text 4 plugin environment. More information on tree-sitter is available here: https://tree-sitter.github.io/tree-sitter/
3. "tree-sitter-java" file folder: A language binding file to allow tree sitter to be used from Java. More information on tree-sitter is available here: https://tree-sitter.github.io/tree-sitter/


This tool is dependent on the following libraries:
1. Tree-sitter to parse user code; more information available here: https://tree-sitter.github.io/tree-sitter/
2. Beautiful Soup to scrape information from web pages; more information available here: https://pypi.org/project/beautifulsoup4/
3. Python Requests library to send HTTP requests to Google; more information available here: https://pypi.org/project/requests/


This tool calls the following APIs:
1. StackExchange API to query Stack Overflow; more information available here: https://api.stackexchange.com/

Setup:
To setup the plugin for use in your Sublime Text 4 IDE, the following steps are required.
1. Install or set-up required libraries:
	1. Beautiful Soup: run command "pip install beautifulsoup4"
	2. Requests: run command "pip install requests"
	3. Tree-sitter: 
		1. Copy folder "tree-sitter"
		2. Open Sublime Text 4
		3. Open Preferences > Browse Packages. This will open the Packages folder.
		4. Go to "Lib/python3.8" folder. Lib is stored under the same directory as the packages folder i.e. need to go up one folder level.
		5. Paste "tree-sitter" folder in "Lib/python3.8"
	4. Tree-sitter library bindings:
		1. Copy folder "tree-sitter-java"
		2. Paste somewhere locally.
2. Get necessary API keys:
	- StackExchange API: See https://api.stackexchange.com/docs
3. Create an empty txt file to save generated code numbers/code id. If you want to start with a specific code number, type this number in and save. Leaving the file empty will default to starting code_id with 1 and increment by 1.
4. Update code in "QueryEvaluationCommand.py" with user dependent information. Make sure that paths are absolute not relative paths.
	- Update stackexchange_key with those received in Step 2.
	- Update tree-sitter path to "tree-sitter" location in "Lib/python3.8" as described in Step 1.
	- Update tree_sitter_lib_path to local copy of "tree-sitter-java"
	- Update logger_path to where you want to save your log files.
	- Update code_number_path to where you have created the txt file as described in Step 3.
5. Move updated "QueryEvaluationCommand.py" to Sublime plugin directory
	- Open Sublime Text 4
	- Go to Preferences > Browse Packages
	- Go to User
	- Paste updated "QueryEvaluationCommand.py"
6. Plugin should now be setup and ready for use. 


Usage:
Once the above setup is completed, the plugin can be called directly from the Sublime Text 4 console.
1. Open Java project file.
2. Make sure Sublime build system is Java by going to Tools > Build System and selecting "JavaC"
3. Build project
4. If there is a compiler error, call the plugin using the following steps:
	- Open the Python console (Ctrl + `)
	- Type view.run_command("query_evaluation")
5. Plugin will automatically create and run the 72 combinations, logging results in result_logger.
6. Wait until "Done for code number: [code_number]" message appears in console.
7. Repeat steps for next code file with compiler error.

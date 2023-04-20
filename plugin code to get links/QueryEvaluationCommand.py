import sublime
import sublime_plugin
import re
import sys
import logging
import os
if '/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages' not in sys.path:
    sys.path.append('/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages')
import ctypes
import requests
import urllib.parse
from bs4 import BeautifulSoup
from tree_sitter import Language, Parser

#set constants
NUM_ANSWER = 10


#update API keys for StackExchange here
stackexchange_key = ...
#update tree-sitter build path
tree_sitter_path = ...
#update tree-sitter library path
tree_sitter_lib_path = ...
#update logger path
logger_path = ...
#update code number counter file path
code_number_path = ...


#setup loggers
def setup_logger(name, log_file, level = logging.INFO):
	log_file = logger_path + log_file
	logger = logging.getLogger(f"{logger_path+name}")
	if (logger.hasHandlers()):
		logger.handlers.clear()
	handler = logging.FileHandler(filename = log_file, mode = "a")
	formatter = logging.Formatter('%(message)s')
	handler = logging.FileHandler(log_file)
	handler.setFormatter(formatter)
	logger.setLevel(level)
	logger.addHandler(handler)
	return logger

result_logger = setup_logger('result_logger', 'result_logger.log')
code_logger = setup_logger('code_logger', 'code_logger.log')
link_logger = setup_logger('link_logger', 'link_logger.log')
query_logger = setup_logger('query_logger','query_logger.log')


#setup tree parser
Language.build_library(
	f'{tree_sitter_path}',
	[
	f'{tree_sitter_lib_path}'
	]
)
JAVA_LANGUAGE = Language(f'{tree_sitter_path}', 'java')
parser = Parser()
parser.set_language(JAVA_LANGUAGE)

#parse code using tree-sitter and return syntax tree
def getSyntaxTree(code):
	tree = parser.parse(bytes(code, "utf8"))
	return tree


#list of all paths from tree
def dfsTree(node, result = [], path = []):
    path.append(node)
    if len(node.children)==0:
        result.append(path.copy())
        path.pop()
    else:
        for child in node.children:
            dfsTree(child, result, path)
        path.pop()
    return result


#traverse syntax tree and return relevant nodes i.e. relevant path
def traverseTree(tree, error_line):
	#index of line number of the tree starts at zero therefore minus one.
	error_line = error_line-1
	root_node = tree.root_node
	paths = dfsTree(root_node, [], [])
	for path in paths:
		last = path[-1]
		if (last.start_point[0] == error_line) and (last.end_point[0] == error_line):
			return path


#find identifiers index locations within relevant part of tree
def findIdentifiers(node):
    #if leaf then return if they have any identifier.
    if node.children == []:
        if node.type == "identifier":
            identifiers = [(node.start_point, node.end_point)]
        else:
            identifiers = []
        return identifiers
    else:
        identifiers = []
        for i in node.children:
            identifiers = identifiers + findIdentifiers(i)
    return identifiers



#removes identifier from relevant part of code. uses traverseTree to find relevant nodes,
#if the error node is only one line, go back to the parent node, else just use the code within that node.
#identifier will be removed using findIdentifiers to be replaced with "x" or blank
def cleanTreeCode(tree, error_line, code):
	relevant_nodes = traverseTree(tree, error_line)
	node = relevant_nodes[-1]
	#if node is only one line, go back to parent.
	index = 1
	while ((index <= len(relevant_nodes)) and (node.end_point[0] == node.start_point[0])):
		node = relevant_nodes[-index]
		index+=1
	start_point = node.start_point
	end_point = node.end_point
	#get index location of identifiers
	identifiers = findIdentifiers(node)
	#get relevant part of code
	code = code.split("\n")
	relevant_code = code[start_point[0]:end_point[0]+1]
	orig_relevant_code = code[start_point[0]:end_point[0]+1]
	relevant_code_dict = {}
	for i in identifiers:
		identifier_line = i[0][0] - start_point[0]
		identifier = relevant_code[identifier_line][i[0][1]:i[1][1]]
		if identifier.strip()!= "":
			try:
				relevant_code_dict[int(identifier_line)] = relevant_code_dict[identifier_line] + [identifier]
			except:
				relevant_code_dict[int(identifier_line)] = [identifier]
	relevant_code_string_x = ""
	relevant_code_string_blank = ""
	for i in range(len(relevant_code)):
		codeX = relevant_code[i]
		codeBlank = relevant_code[i]
		try:
			for identifier in relevant_code_dict[i]:
				codeX = re.sub(r'\b' + identifier.strip() + r'\b', "x", codeX)
				codeBlank = re.sub(r'\b' + identifier.strip() + r'\b', "", codeBlank)
		except:
			pass
		relevant_code_string_x = relevant_code_string_x + (codeX.strip()) + " "
		relevant_code_string_blank = relevant_code_string_blank + (codeBlank.strip()) + " "
	return (str(orig_relevant_code), relevant_code_string_x, relevant_code_string_blank)

#remove error line identifiers
def removeIdentifier(code):
	tree2 = getSyntaxTree(code)
	node = tree2.root_node
	identifiers = findIdentifiers(node)
	#get relevant part of code
	code = code.split("\n")
	start_point = node.start_point
	end_point = node.end_point
	relevant_code = code[start_point[0]:end_point[0]+1]
	orig_relevant_code = code[start_point[0]:end_point[0]+1]
	relevant_code_dict = {}
	for i in identifiers:
		identifier_line = i[0][0] - start_point[0]
		identifier = relevant_code[identifier_line][i[0][1]:i[1][1]]
		if identifier.strip()!= "":
			try:
				relevant_code_dict[int(identifier_line)] = relevant_code_dict[identifier_line] + [identifier]
			except:
				relevant_code_dict[int(identifier_line)] = [identifier]
	relevant_code_string = ""
	for i in range(len(relevant_code)):
		code = relevant_code[i]
		try:
			for identifier in relevant_code_dict[i]:
				code = re.sub(r'\b' + identifier.strip() + r'\b', "", code)
		except:
			pass
		relevant_code_string = relevant_code_string + (code.strip()) + " "
	return relevant_code_string



#extract error message from compiler message.
def extractErrorMessage(compiler_message):
	lines = compiler_message.split("\n")
	#check if there are any errors when building program.
	if (len(lines) < 2):
		return -1
	#get error message and code that produced error
	for line in lines:
		if "error: " in line:
			#only get text after "error"
			error_message = re.search("(?<=error:\s).*", line).group()
			line_error = re.search(":([0-9]+): error:", line).group(1)
			#code with error would be printed on next line after the error message
			code_error = lines[lines.index(line)+1].strip()
			break
	return (error_message, code_error, line_error)

#extract file name from compiler message.
def extractFileName(compiler_message):
	lines = compiler_message.split("\n")
	#check if there are any errors when building program.
	if (len(lines) < 2):
		return -1
	#get file name
	for line in lines:
		if "error: " in line:
			#only get text after "error"
			path = re.search(".+?(?=:[0-9]+:)", line).group()
			break
	filename = path.split(os.sep)[-1]
	return (filename, path)

#remove variable / other identifiers from error messages encountered.
def genericError(error_message):
	if "might not have been initialized" in error_message:
		return "variable might not have been initialized"
	elif ("incompatible types" in error_message) and ("cannot be converted to" in error_message):
		return "incompatible types: X cannot be converted to Y"
	elif "cannot be referenced from a static context" in error_message:
		return "non-static method cannot be referenced from a static context"
	elif "is public, should be declared in a file named" in error_message:
		return "class X is public, should be declared in a file named X.java"
	elif "incompatible types: possible lossy conversion from" in error_message:
		return "incompatible types: possible lossy conversion from"
	elif "required, but" and "found" in error_message:
		return "X required, but Y found"
	elif "bad operand types for binary operator" in error_message:
		return "bad operand types for binary operator"
	elif "cannot be dereferenced" in error_message:
		return "cannot be dereferenced"
	elif "is already defined in method" in error_message:
		return "variable X is already defined in method Y"
	elif "cannot assign a value to final variable" in error_message:
		return "cannot assign a value to final variable"
	elif "no suitable method found for" in error_message:
		return "no suitable method found for"
	elif ("method " in error_message) and (" class " in error_message) and ("cannot be applied to given types" in error_message):
		return "method X in class Y cannot be applied to given types"
	else:
		return error_message

#make search request to stackexchange API. Get json object and number of objects returned
def searchRequest(error_message):
	#add java tag to error message as the search query on stackexchange
	error_message = "java " + error_message
	search_message = urllib.parse.quote(error_message)
	key = f'{stackexchange_key}'
	ep = "/2.3/search?order=desc&sort=relevance&tagged=java&intitle={}&site=stackoverflow".format(search_message)
	res = requests.get("https://api.stackexchange.com"+ep+"&key="+key)
	res = res.json()
	try:
		num_results = len(res["items"])
	except:
		num_results = 0
	return (res, num_results)

#get link by searching stackoverflow from google for when stackexchange returns no result
def searchGoogleLink(error_message):
	#get top stackoverflow result from google
	error_message =  "\"java\"" + " error " + error_message + " site:stackoverflow.com"
	search_message = urllib.parse.quote(error_message)
	headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0'}
	res = requests.get("https://google.com/search?q={}".format(search_message), headers = headers)
	res.raise_for_status()
	soup = BeautifulSoup(res.text, "html.parser")
	#get number of results found
	num_results = soup.find("div", {"id": "result-stats"})
	try:
		num_results = int(float(num_results.text.split(' ')[1].replace(',','')))
	except:
		num_results = "error converting number of results"
	#get urls
	all_url = []
	for result in soup.select('.tF2Cxc'):
		link = result.select_one('.yuRUbf a')['href']
		if not bool(re.search("https://stackoverflow.com",str(link))):
			continue
		else:
			url = re.search("https://(.*)", link).group()
			all_url.append(url)
	if not (len(all_url)==0):
		return (all_url, num_results)
	else:
		return None

#get top result url from search request
def topResultLinks(result_json):
	links = []
	for i in result_json["items"]:
		#check that post is answered
		if i["is_answered"]:
			links.append(i["link"])
	return links


#get answer from stackoverflow
def getAnswer(url):
	res = requests.get(url)
	soup = BeautifulSoup(res.text, 'html.parser')
	# if answer is accepted
	pos = False
	acc = False
	try:
		answer_class =  soup.find('div', attrs ={'class':'answer js-answer accepted-answer js-accepted-answer'})
		answer = answer_class.find('div',attrs={'class':'s-prose js-post-body'}).getText()
		acc = True
		vote = answer_class.find('div', attrs = {'class':'js-vote-count flex--item d-flex fd-column ai-center fc-black-500 fs-title'}).getText()
		if vote > 0:
			return (answer, "ACP")
		else:
			pass
	except:
		pass
	# if we want no accepted answer but exist positively rated answer
	# get the first answer as it is sorted by score.
	try:
		answer_class = soup.find('div', attrs ={'class':'answer js-answer'})
		answer = answer_class.find('div',attrs={'class':'s-prose js-post-body'}).getText()
		vote = answer_class.find('div', attrs = {'class':'js-vote-count flex--item d-flex fd-column ai-center fc-black-500 fs-title'}).getText()
		vote = int(vote)
		if vote > 0:
			if acc == True:
				return (answer, "ACP")
			else:
				return (answer, "POS")
		else:
			if acc == True:
				return (answer, "ACC")
			else:
				return (answer, "ANY")
	except:
		return None
	return None


#Main command. Creates empty panel to print error message and calls get_compiler_message
class QueryEvaluationCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		#create a new empty panel to print error message
		self.panel = self.view.window().create_output_panel('error_output')
		self.view.window().run_command('show_panel', { 'panel': 'output.error_output' })
		#get error message and print on new panel
		self.panel.run_command('get_compiler_message');

#Gets compiler message, calls StackExchange API and prints enhanced error message.
#StackExchange is intentionally quite limited, thus if no results are found, search will be done on google.
class GetCompilerMessageCommand(sublime_plugin.TextCommand):	
	def run(self, edit):
		unique_links = []
		#get compiler message and code
		w = sublime.active_window()
		v = w.find_output_panel("exec")
		compiler_message = v.substr(sublime.Region(0, v.size()))
		#get error message and relevant parts of code 
		error_details = extractErrorMessage(compiler_message)
		#get file details
		file_details = extractFileName(compiler_message)
		filename = file_details[0]
		filepath = file_details[1]
		#use file details to get code to put in parser
		#v2 = w.find_open_file(filepath)
		#code = v2.substr(sublime.Region(0, v.size()))

		with open(filepath) as f:
			code = f.read()
			f.close()

		links = []
		answers = []
		summ_answers = []
		answer = None
		#if no build errors print as so.
		if error_details == -1:
			success_message = "Program built successfully with no compiler errors."
			self.view.insert(edit, self.view.size(), success_message)
		else:
			#get code number to identify log
			with open(code_number_path,'r') as f:
				lines = f.read().splitlines()
				if len(lines)==0:
					code_number = 1
				else:
					code_number = int(lines[-1])+1
				f.close()
			

			error_message = error_details[0]
			code_error = error_details[1]
			code_error_clean = removeIdentifier(code_error)
			line_error = error_details[2]
			#use tree sitter to parse tree and get relevant parts of code with identifiers removed.
			#See cleanTreeCode function for more informeation.
			tree = getSyntaxTree(code)
			relevant_code = cleanTreeCode(tree, int(line_error), code)
			relevant_code_orig = relevant_code[0]
			relevant_code_x = relevant_code[1]
			relevant_code_blank = relevant_code[2]
			#remove parameters / other things inside brackets of code
			relevant_code_orig = re.sub(r'\([^)]*\)', '()', relevant_code_orig)
			relevant_code_x = re.sub(r'\([^)]*\)', '()', relevant_code_x)
			relevant_code_blank = re.sub(r'\([^)]*\)', '()', relevant_code_blank)
			#remove apostrophe's from tree sitter results.
			relevant_code_orig = relevant_code_orig.replace("\'","")
			relevant_code_x = relevant_code_x.replace("\'","")
			relevant_code_blank = relevant_code_blank.replace("\'","")
			generic_error = genericError(error_message)


			#different types of query elements available
			#error_or = original error message
			#error_cu = error message with custom treatment of identifiers
			#code_no = no code included in query
			#code_li = line of code that throws error
			#code_lw = line of code that throws error with identifiers removed
			#code_pa = parent node of line of code that throws error
			#code_pw = parent node of line of code that throws error with identifiers removed
			#code_px = parent node of line of code that throws error with identifiers replaced with "x"

			error_or = error_message
			error_cu = generic_error
			code_no = ""
			code_li = code_error
			code_lw = code_error_clean
			code_pa = relevant_code_orig
			code_pw = relevant_code_blank
			code_px = relevant_code_x

			#create different queries based on 

			or_no = error_or + " " + code_no
			or_li = error_or + " " + code_li
			or_lw = error_or + " " + code_lw
			or_pa = error_or + " " + code_pa
			or_pw = error_or + " " + code_pw
			or_px = error_or + " " + code_px
			cu_no = error_cu + " " + code_no
			cu_li = error_cu + " " + code_li
			cu_lw = error_cu + " " + code_lw
			cu_pa = error_cu + " " + code_pa
			cu_pw = error_cu + " " + code_pw
			cu_px = error_cu + " " + code_px

			all_queries_name = ["or_no", "or_li", "or_lw", "or_pa", "or_pw", "or_px", "cu_no", "cu_li", "cu_lw", "cu_pa", "cu_pw", "cu_px"]
			all_queries = [or_no, or_li, or_lw, or_pa, or_pw, or_px, cu_no, cu_li, cu_lw, cu_pa, cu_pw, cu_px]

			types = ["s_any","s_pos","s_acc","g_any","g_pos","g_acc"]

			my_dict = {}
			num_results_dict = {}

			#initialise answer set
			for i in types:
				for j in all_queries_name:
					my_dict[i+"_"+j] = []
					num_results_dict[i+"_"+j] = 0


			query_index = 0
			for query in all_queries:

				#stackexchange API (i.e. s_XXX)
				stack = searchRequest(query)
				if stack == None:
					stack_results = None
					stack_num_results = 0
				else:
					result_json, stack_num_results = stack
					stack_results = topResultLinks(result_json)
				s_any_name = "s_any_" + all_queries_name[query_index]
				s_pos_name = "s_pos_" + all_queries_name[query_index]
				s_acc_name = "s_acc_" + all_queries_name[query_index]

				num_results_dict[s_any_name] = (query, stack_num_results)
				num_results_dict[s_pos_name] = (query, stack_num_results)
				num_results_dict[s_acc_name] = (query, stack_num_results)

				if not (stack_results==None):
					for link in stack_results:
						if link not in unique_links:
							unique_links.append(link)
						if (len(my_dict[s_pos_name]) <= NUM_ANSWER) and (len(my_dict[s_acc_name]) <= NUM_ANSWER) and not (link in my_dict[s_any_name]):
							page_result = getAnswer(link)
							if (not (page_result == None)) :
								ans_type = page_result[1]
								#accepted answer exist and is positively voted
								if ans_type == "ACP":
									my_dict[s_any_name].append(link)
									my_dict[s_pos_name].append(link)
									my_dict[s_acc_name].append(link)
								#accepted answer exist but not positively voted
								elif ans_type == "ACC":
									my_dict[s_acc_name].append(link)
									my_dict[s_any_name].append(link)
								#no accepted answer but positively rated answer exist
								elif ans_type == "POS":
									my_dict[s_pos_name].append(link)
									my_dict[s_any_name].append(link)
								else:
									my_dict[s_any_name].append(link)
						else:
							break

				#google search (i.e. g_XXX)
				google = searchGoogleLink(query)
				if google == None:
					google_results = None
					google_num_results = 0
				else:
					google_results, google_num_results = google
				g_any_name = "g_any_" + all_queries_name[query_index]
				g_pos_name = "g_pos_" + all_queries_name[query_index]
				g_acc_name = "g_acc_" + all_queries_name[query_index]

				num_results_dict[g_any_name] = (query, google_num_results)
				num_results_dict[g_pos_name] = (query, google_num_results)
				num_results_dict[g_acc_name] = (query, google_num_results)

				if not (google_results == None):
					for link in google_results:
						if link not in unique_links:
							unique_links.append(link)
						if (len(my_dict[g_acc_name]) <= NUM_ANSWER) and (len(my_dict[g_pos_name]) <= NUM_ANSWER) and not (link in my_dict[g_any_name]):
							page_result = getAnswer(link)
							if (not (page_result == None)):
								ans_type = page_result[1]
								#accepted answer exist and is positively voted
								if ans_type == "ACP":
									my_dict[g_any_name].append(link)
									my_dict[g_pos_name].append(link)
									my_dict[g_acc_name].append(link)
								#accepted answer exist but not positively voted
								elif ans_type == "ACC":
									my_dict[g_acc_name].append(link)
									my_dict[g_any_name].append(link)
								#no accepted answer but positively rated answer exist
								elif ans_type == "POS":
									my_dict[g_pos_name].append(link)
									my_dict[g_any_name].append(link)
								else:
									my_dict[g_any_name].append(link)
						else:
							break
				query_index+=1

			
			#update code/file number
			with open(code_number_path,'a') as f:
				f.write(str(code_number)+"\n")
				f.close()

			#log relevant information.
			code_logger.info("------" + str(code_number) + "------")
			code_logger.info(code)
			code_logger.info("\n")
			for i in range(len(all_queries)):
				query_save = str(code_number) + ", " + all_queries_name[i] + ", " +all_queries[i]
				query_logger.info(query_save)

			for link in unique_links:
				link_logger.info(str(code_number) + "," + link)

			for i in types:
				for j in all_queries_name:
					option = i+"_"+j
					option_csv = option.replace("_",",")
					num_result = num_results_dict[option][1]
					csv = str(code_number) + "," + option_csv+","+str(num_result)
					links = my_dict[option]
					for link in links:
						csv = csv + "," + link
					result_logger.info(csv)

			self.view.insert(edit, self.view.size(), "Done for code number: " + str(code_number))



			

    


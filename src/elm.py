'''import librarries'''
import re
import os
import ast
import xml.etree.ElementTree as ET
import spacy
import openai

#load language library
nlp = spacy.load('en_core_web_sm')

def connect_to_openai():
    '''authorise the connection to OpenAI api'''
    openai.organization = "org-WTPCAZdWARkJoItCjU9VV1WE"
    openai.api_key = ""
    openai.Model.list()
    model_name = "gpt-3.5-turbo"
    return model_name

def get_response(model_input, instruction, hint_input):
    '''method to request suggestion from OpenAI API'''
    response = openai.ChatCompletion.create(
        model=model_input,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": hint_input},
        ],
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    return response['choices'][0]['message']['content']

def enterprise_finetuning(code_input, match_replace):
    '''replacing config key-matches in response text'''
    for match in match_replace:
            if str(match) !='{}':
                for key, value in match.items():
                    if key in code_input:
                        code_input=code_input.replace(key, value)
    return code_input

def get_config_match(match_input, match_replace):
    '''find the config keys from configuration'''
    matched=''
    for match in match_replace:
            if str(match) !='{}':
                for key, value in match.items():
                    if key == match_input:
                        matched=value
    return str(matched)

def read_lang_config(tag_value, lang_input):
    '''read from language configuration files'''
    current_dir = os.path.dirname(__file__)
    tree = ET.parse(current_dir + "/" + lang_input + "-config.xml")
    root = tree.getroot()
    match_replace_list=[{}]
    for child in root:
        match_dict=child.attrib
        match = match_dict.get(tag_value)
        replace=child.text
        match_replace={match: replace}
        match_replace_list.append(match_replace)
    return match_replace_list

def refine_methods(enterprise_name, lang, code):
    '''apply enterprise code conventions on methods'''
    if lang=='python':
        tree = ast.parse(code)
        function_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name_part=node.name.split('_')
                if (enterprise_name.lower() not in name_part):
                    if ('fn' in name_part):
                        code = code.replace(node.name, enterprise_name.lower() + '_' + node.name)
                    else:
                        code = code.replace(node.name, enterprise_name.lower() + '_fn_' + node.name)
                else:
                    if ('fn' not in name_part):
                        code = code.replace(enterprise_name.lower() + '_', enterprise_name.lower() + '_fn_')
    elif lang=='sql':
        pattern = r'CREATE\s+FUNCTION\s+(\w+)'
        function_names = re.findall(pattern, code, re.IGNORECASE)
        for name in function_names:
            name_part=name.split('_')
            if (enterprise_name.lower() not in name_part):
                if ('fn' in name_part):
                    code = code.replace(name, enterprise_name.lower() + '_' + name)
                else:
                    code = code.replace(name, enterprise_name.lower() + '_fn_' + name)
            else:
                if ('fn' not in name_part):
                    code = code.replace(enterprise_name.lower() + '_', enterprise_name.lower() + '_fn_')
        pattern = r'CREATE\s+PROCEDURE\s+(\w+)'
        sp_names = re.findall(pattern, code, re.IGNORECASE)
        for name in sp_names:
            name_part=name.split('_')
            if (enterprise_name.lower() not in name_part):
                if ('sp' in name_part):
                    code = code.replace(name, enterprise_name.lower() + '_' + name)
                else:
                    code = code.replace(name, enterprise_name.lower() + '_sp_' + name)
            else:
                if ('sp' not in name_part):
                    code = code.replace(enterprise_name.lower() + '_', enterprise_name.lower() + '_sp_')
    return code

def remove_passwords(hint):
    '''replace the confidential credentials from input text'''
    pattern = r"\b[A-Za-z0-9@#$%^&+=]{8,}\b"
    return re.sub(pattern, "password", hint)

def remove_api_keys(hint):
    '''remove confidential keys from input text'''
    pattern = r"[A-Za-z0-9]{32}"
    return re.sub(pattern, "sample-key-", hint)

def remove_bank_details(hint):
    '''remove the bank details from input text'''
    pattern = r"\b(?:\d{4}-){3}\d{4}\b|\b(?:\d{4} ){3}\d{4}\b|\b(?:\d{4}\.){3}\d{4}\b"
    return re.sub(pattern, "", hint)

def remove_personal_details(hint):
    '''remove individual information from input text'''
    pattern = r'\b(\d{4}-\d{2}-\d{2}|\d{3}-\d{2}-\d{4}|(\d{3}\s?){3}|\d{4}\s\d{4}\s\d{4}\s\d{4})\b'
    return re.sub(pattern, '[REDACTED]', hint)

def change_named_entity(hint):
    '''replace the organization names used into input text'''
    doc=nlp(hint)
    for ent in doc.ents:
        if ent.label_ == 'ORG':
            hint = hint.replace(ent.text, 'NAMED_ENTITY')
    return hint

def clean_hint(txt):
    '''clean the input text for text preprocessing'''
    txt=txt.lower()
    return txt

def lemmatize_txt(txt):
    '''lemmatize input text to produce more meaningful and language friendly word tokens for input'''
    sentence=[]
    document=nlp(txt)
    for word in document:
        sentence.append(word.lemma_)
    return " ".join(sentence)

def tokenize_sentence(hint):
    '''tokenize the input text to remove unwanted word tokens and reduce the overall token size'''
    doc = nlp(hint)
    filtered_tokens = [token.text for token in doc if token.is_stop == False]
    filtered_hint=''
    for ftoken in filtered_tokens:
        filtered_hint=filtered_hint + ' ' + ftoken
    return filtered_hint

def case_conversion(code, case):
    '''apply variable naming case convention as per the enterprise language configuration'''
    tree = ast.parse(code)
    variables = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            variables.add(node.id)
    for variable in variables:
        var=variable
        if(case == 'pascal'):
            var = variable.replace("_", " ").title().replace(" ", "")
        elif (case == 'snake'):
            var = [variable[0].lower()]
            for c in variable[1:]:
                if c in ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
                    var.append('_')
                    var.append(c.lower())
                else:
                    var.append(c)
            var = ''.join(var)
        elif (case == 'camel'):
            var = variable.split('_')
            var = var[0] + ''.join(ele.title() for ele in var[1:])
        code = code.replace(variable, var)
    return code

def code_complete(lang, hint):
    '''main mathod to trigger the code completion processing'''
    model = connect_to_openai()
    attrib_lang = read_lang_config("match", lang)
    instructions=get_config_match('instructions', attrib_lang)
    instructions=instructions.replace('lang_name', lang)
    hint = clean_hint(hint)
    hint = lemmatize_txt(hint)
    hint = remove_api_keys(hint)
    hint=change_named_entity(hint)
    hint_suffix=get_config_match('hint_suffix', attrib_lang)
    hint = hint + hint_suffix
    hint = tokenize_sentence(hint)
    code = get_response(model, instructions, hint)
    code = enterprise_finetuning(code, attrib_lang)
    attrib_enterprise = read_lang_config("match", 'enterprise')
    enterprise_name = get_config_match('enterprise_name', attrib_enterprise)
    case=get_config_match('case', attrib_lang)
    code = case_conversion(code, case)
    code = refine_methods(enterprise_name, lang, code)
    initial_comment=get_config_match('initial_comment', attrib_lang)
    initial_comment=initial_comment.replace('enterprise_name', enterprise_name)
    code = initial_comment + '\n' + code
    return code

'''Model Test'''
gen_code = code_complete('python','declare 3 variable EmployeeName, employeeAge and employeeSalary using pascal case')
print(gen_code)

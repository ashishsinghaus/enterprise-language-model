'''import librarries'''
import re
import os
import xml.etree.ElementTree as ET
import openai
import ast
import nltk
import spacy
import string

nlp = spacy.load('en_core_web_sm')

'''Necessary downloads for NLTK'''
'''nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')'''

def connect_to_openai():
    '''method to connect with OpenAI API'''
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
    '''method to finetune the suggested code for enterprise'''
    for match in match_replace:
            if str(match) !='{}':
                for key, value in match.items():
                    if key in code_input:
                        code_input=code_input.replace(key, value)
    return code_input

def get_config_match(match_input, match_replace):
    '''method to finetune the suggested code for enterprise'''
    matched=''
    for match in match_replace:
            if str(match) !='{}':
                for key, value in match.items():
                    if key == match_input:
                        matched=value
    return str(matched)

def read_lang_config(tag_value, lang_input):
    '''method to read language configurations'''
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
    if lang=='python':
        tree = ast.parse(code)
        function_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                code = code.replace(node.name, enterprise_name.lower() + '_fn_' + node.name)
    elif lang=='sql':
        pattern = r'CREATE\s+FUNCTION\s+(\w+)'
        function_names = re.findall(pattern, code, re.IGNORECASE)
        for fname in function_names:
            code = code.replace(fname, enterprise_name.lower() + '_fn_' + fname)
        pattern = r'CREATE\s+PROCEDURE\s+(\w+)'
        sp_names = re.findall(pattern, code, re.IGNORECASE)
        for sname in sp_names:
            code = code.replace(sname, enterprise_name.lower() + '_sp_' + sname)

    return code

def find_sp_names(sql_script):
    pattern = r'CREATE\s+PROCEDURE\s+(\w+)'
    stored_procedures = re.findall(pattern, sql_script, re.IGNORECASE)
    return stored_procedures

def remove_passwords(hint):
    pattern = r"\b[A-Za-z0-9@#$%^&+=]{8,}\b"
    return re.sub(pattern, "password", hint)

def remove_api_keys(hint):
    pattern = r"[A-Za-z0-9]{32}"
    return re.sub(pattern, "sample-key-", hint)

def remove_bank_details(hint):
    pattern = r"\b(?:\d{4}-){3}\d{4}\b|\b(?:\d{4} ){3}\d{4}\b|\b(?:\d{4}\.){3}\d{4}\b"
    return re.sub(pattern, "", hint)

def remove_personal_details(hint):
    pattern = r'\b(\d{4}-\d{2}-\d{2}|\d{3}-\d{2}-\d{4}|(\d{3}\s?){3}|\d{4}\s\d{4}\s\d{4}\s\d{4})\b'
    return re.sub(pattern, '[REDACTED]', hint)

def change_named_entity(hint):
    doc=nlp(hint)
    for ent in doc.ents:
        if ent.label_ == 'ORG':
            hint = hint.replace(ent.text, 'NAMED_ENTITY')
    return hint

def clean_hint(txt):
    txt=txt.lower()
    return txt

def lemmatize_txt(txt):
    sentence=[]
    document=nlp(txt)
    for word in document:
        sentence.append(word.lemma_)
    return " ".join(sentence)

def tokenize_sentence(hint):
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(hint)
    filtered_tokens = [token.text for token in doc if token.is_stop == False]
    filtered_hint=''
    for ftoken in filtered_tokens:
        filtered_hint=filtered_hint + ' ' + ftoken
    return filtered_hint

def code_suggest(lang, hint):
    model = connect_to_openai()

    attrib = read_lang_config("match", lang)
    instructions=get_config_match('instructions', attrib)
    attrib = read_lang_config("match", lang)
    instructions=instructions.replace('lang_name', lang)

    hint = clean_hint(hint)
    hint = lemmatize_txt(hint)
    #hint = remove_passwords(hint)
    hint=change_named_entity(hint)

    attrib = read_lang_config("match", lang)
    hint_prefix=get_config_match('hint_prefix', attrib)
    hint = hint_prefix + hint

    #hint = tokenize_sentence(hint)

    print(hint)

    code = get_response(model, instructions, hint)

    attrib = read_lang_config("match", lang)
    code = enterprise_finetuning(code, attrib)

    attrib = read_lang_config("match", 'enterprise')
    enterprise_name = get_config_match('enterprise_name', attrib)

    code = refine_methods(enterprise_name, lang, code)

    attrib = read_lang_config("match", lang)
    initial_comment=get_config_match('initial_comment', attrib)

    initial_comment=initial_comment.replace('enterprise_name', enterprise_name)
    code = initial_comment + '\n' + code
    #HINT = remove_api_keys(HINT)
    return code

gen_code = code_suggest('python','write code to find the file extension')
print(gen_code)

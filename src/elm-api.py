from flask import Flask, jsonify, request
from elm import code_complete

# instance of flask application
app = Flask(__name__)
 
# home route that returns below text when root url is accessed
@app.route("/")
def code_complete():
    lang = request.args.get('lang')
    hint = request.args.get('hint')
    return code_complete(lang, hint)
 
if __name__ == '__main__': 
   app.run()

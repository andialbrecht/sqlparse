from flask import Flask, make_response

from sqlformat.legacy import legacy


app = Flask('sqlformat')


@app.route('/ping')
def ping():
    return make_response('pong')

@app.route('/_ah/warmup')
def warmup():
    return make_response('polishing chrome')


# Register legacy URLs last so that newer URLs replace them.
app.register_blueprint(legacy)

#!/usr/bin/python
import subprocess
from bottle import request, Bottle, abort
app = Bottle()


@app.route('/websocket')
def handle_websocket():
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request.')

    while True:
        try:
            message = wsock.receive()
            if(len(message)==0):
                continue
            #print message
            #inputs =  message.replace(',',' ')
            inputs  = message.split(",")
            print inputs
            cmd = list()
            cmd.append('/Users/bbiiggppiigg/Sites/gmarket_report/search2.py')
            #print message.split()
            proc = subprocess.Popen(cmd+inputs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            while True:
                stri = proc.stdout.readline()
                if("par_crawler main thread after execution\n"==stri):
                    wsock.send("work done")
                    break
                elif(len(stri)!=0):
                    wsock.send(stri)

            #wsock.send("Your message was: %r" % inputs)
        except WebSocketError, e:
            print e
            break

from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
server = WSGIServer(("0.0.0.0", 8080), app,
                    handler_class=WebSocketHandler)
server.serve_forever()

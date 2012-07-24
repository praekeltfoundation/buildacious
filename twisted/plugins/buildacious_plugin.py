from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.web import static, server, resource, client
from twisted.internet import defer, reactor, threads, utils, task

import json, os

class Buildacious(resource.Resource):
    isLeaf = True
    addSlash = True

    def __init__(self):
        self.currentWorkers = {}
        reactor.callWhenRunning(self.startCore)

    def startCore(self):
        self.task = task.LoopingCall(self.coreLoop)
        self.task.start(5.0)

    def endJob(self, res, job):
        out, err, signalNum = res
        if signalNum > 0:
            print "Job died:", job
            os.remove(os.path.join('/var/www/buildacious/uploads', job))
            del self.currentWorkers[job]
        else:
            print "Job end:",job, out
            os.remove(os.path.join('/var/www/buildacious/uploads', job))
            del self.currentWorkers[job]

            f = open('/var/www/buildacious/completed', 'at')
            f.write(job+'\n')
            f.close()

    def coreLoop(self):
        tasks = os.listdir('/var/www/buildacious/uploads')

        for t in tasks:
            if t not in self.currentWorkers:
                # Spawn the upload
                job, sc = open('/var/www/buildacious/uploads/'+t).read().split('\n')

                print "Spawning", job, sc
                self.currentWorkers[t] = utils.getProcessOutputAndValue(
                    '/usr/bin/dput', args=('ppa:praekeltfoundation/ppa', os.path.join(job,sc)), path=job
                ).addBoth(self.endJob, t)

        if self.currentWorkers:
            print "Current workers:", self.currentWorkers


    def completeCall(self, response, request):
        # Render the json response from call
        response = json.dumps(response)
        request.write(response)
        request.finish()

    def render_GET(self, request):
        request.setHeader("content-type", "application/json")
        
        print dir(request)

        return "buildacious"

    def render_POST(self, request):
        request.setHeader("content-type", "application/json")
        # Get request 
        command = cgi.escape(request.args["command"][0])
        params = json.loads(cgi.escape(request.args["params"][0]))

        d.addCallback(self.completeCall, request)

        return server.NOT_DONE_YET

class Options(usage.Options):
    optParameters = [["port", "p", 6012, "The port to listen on."]]

class MyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "buildacious"
    description = "Buildacious bot"
    options = Options

    def makeService(self, options):
        return internet.TCPServer(int(options["port"]), server.Site(Buildacious()))


serviceMaker = MyServiceMaker()

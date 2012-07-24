from django.shortcuts import get_object_or_404, render_to_response
from django.core.context_processors import csrf
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.utils import simplejson
from django.contrib.auth.decorators import login_required

from django import forms

from lxml import etree

import os

from launchpadlib.launchpad import Launchpad


def parseChanges(fn):
    f = open(fn)

    info = {'scfile': fn.split('/')[-1]}

    for l in f:
        if "Version:" in l and 'version' not in info:
            info['version'] = l.split(':')[-1].strip()
        if "Distribution:" in l:
            info['dist'] = l.split(':')[-1].strip().capitalize()
    return info

@login_required
def upload(request):
    scf = request.get_full_path().split('/')[-1]
    job = request.get_full_path().split('/')[-2]

    f = open('/var/www/buildacious/uploads/'+scf, 'wt')
    f.write('/var/lib/jenkins/jobs/%s/\n%s' % (job, scf))
    f.close()

    return HttpResponseRedirect('/')

#@login_required
def index(request):

    stree = {}

    jobs = os.listdir('/var/lib/jenkins/jobs/') 

    lp = Launchpad.login_anonymously('Praekelt', 'production', '/tmp/lpcache')
    ppa = lp.people['praekeltfoundation'].getPPAByName(name='ppa')
    b = ppa.getPublishedBinaries()

    ppastat = {}

    for i in b:
        n = "%s_%s_source.changes" % (i.binary_package_name, i.binary_package_version)
        ppastat[n] = i.status

    try:
        uploaded = open('/var/www/buildacious/completed').read()
    except:
        uploaded = ""

    # Find sources
    for j in jobs:
        sources = [ i for i in 
            os.listdir(os.path.join('/var/lib/jenkins/jobs/', j))
            if 'source.changes' in i]

        name = j.capitalize()
        if sources: 
            stree[name] = []
            # Parse source.changes files 
            for s in sources:
                buildNum = s.split('+')[-1].split('-')[0]
                info = parseChanges(os.path.join('/var/lib/jenkins/jobs/', j, s))

                status = open(os.path.join('/var/lib/jenkins/jobs/', j,'builds',buildNum, 'build.xml')).read()
                tree = etree.fromstring(status)
                status = tree.xpath('//build/result')[0].text

                upload = os.path.exists('/var/www/buildacious/uploads/'+s)
                if upload:
                    info['uploading'] = True

                if s in uploaded:
                    info['sent'] = True

                info['status'] = status

                info['lpstatus'] = ppastat.get(s, None)
                info['spath'] = j

                stree[name].append(
                    info
                )
        
    print stree

    rendata = {
        'stree': stree
    }
    return render_to_response('index.html', rendata, context_instance=RequestContext(request))

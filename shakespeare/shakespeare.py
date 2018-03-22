#!/usr/bin/env python

import datetime
import functools
import logging
import os
import random
import signal
import time

__version__ = "1.5"
PORT = 5000
HOSTNAME = os.getenv("HOSTNAME")

from flask import Flask, jsonify, request, Response

app = Flask(__name__)

######## Quote storage
#
# Obviously, this would more typically involve a persistent backing store. That's not
# really needed for a demo though.

quotes = [
    "There is nothing either good or bad but thinking makes it so.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_109527",
    "The course of true love never did run smooth.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_109526",
    "Some are born great, some achieve greatness, and some have greatness thrust upon them.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_101484",
    "What's in a name? That which we call a rose by any other name would smell as sweet.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_125207",
    "Good night, good night! Parting is such sweet sorrow, that I shall say good night till it be morrow.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_155061",
    "How far that little candle throws its beams! So shines a good deed in a naughty world.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_155088",
    "Better three hours too soon than a minute too late.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_139153",
    "There is no darkness but ignorance.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_138212",
    "All the world's a stage, and all the men and women merely players: they have their exits and their entrances; and one man in his time plays many parts, his acts being seven ages.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_166828",
    "Cowards die many times before their deaths; the valiant never taste of death but once.  Read more at: https://www.brainyquote.com/quotes/william_shakespeare_104447"
]

######### Shakespeare Quote data
##
## quote, play, verse, character, iambs
shakespeare_data = [
    {'quote': "quote",
     'play': "play",
     'verse': "verse",
     'spaketh': "spaketh",
     'iambs': "iambs"},
    {'quote': "To be, or not to be: that is the question",
     'play': "Hamlet",
     'verse': "Act III, Scene I",
     'spaketh': "Prince Hamlet",
     'iambs': "to BE - or NOT - to BE - that IS - the QUESTION"},
    {'quote': "What's in a name? That which we call a rose by any other name would smell as sweet",
     'play': "Romeo and Juliet",
     'verse': "Act II, Scene II",
     'spaketh': "Juliet",
     'iambs': "what's IN - a NAME - that WHICH - we CALL - a ROSE - by ANY - other NAME - would SMELL - as SWEET"},
    {'quote': "But, soft! What light through yonder window breaks?",
     'play': "Romeo and Juliet",
     'verse': "Act II Scene II",
     'spaketh': "Romeo",
     'iambs': "but SOFT - what LIGHT - through YON - der win - dow BREAKS?"},
    {'quote': "O, Romeo, Romeo, where for art thou, Romeo",
     'play': "Romeo and Juliet",
     'verse': "Act II Scene II",
     'spaketh': "Juliet",
     'iambs': "O ROMeo - ROM eo - WHEREfore - ART thou - ROMeo"},
    {'quote': "Friends, Romans, countrymen lend me your ears. I come to bury Caesar, not praise him!",
     'play': "Julius Caesar",
     'verse': "Act III, Scene II",
     'spaketh': "Mark Antony",
     'iambs': "FRIENDS - ROMANS - COUNTRYMEN - lend ME - your EARS - i COME - to BURY - caesar NOT - praise HIM"},
    {'quote': "All the worlds a stage and all the men and women merely players",
     'play': "As You Like It",
     'verse': "Act II, Scene VII",
     'spaketh': "Jacques",
     'iambs': "all THE - worlds a STAGE - and ALL - the MEN - and WOMEN  - mere LY - play ERS"},
    {'quote': "If music be the food of love, play on",
     'play': "Twelfth Night",
     'verse': "Act I, Scene I",
     'spaketh': "Duke Orsino",
     'iambs': "if MU - sic BE - the FOOD - of LOVE - play ON"},
    {'quote': "Double, double, toil and trouble, fire burn and cauldron bubble",
     'play': "Macbeth",
     'verse': "Act IV, Scene I",
     'spaketh': "Three Witches",
     'iambs': "[Long Trochee] DOUble - DOUble - TOIL and - TROUble - FIre - BURN and - CAULdron - BUbble"},
    {'quote': "Cry 'Havoc!', and let slip the dogs of war",
     'play': "Julius Caesar",
     'verse': "Act III, Scene I",
     'spaketh': "Mark Antony",
     'iambs': "cry HAV - oc AND - let SLIP - the DOGS - of WAR"}
]


######## Utilities

class RichStatus(object):
    def __init__(self, ok, **kwargs):
        self.ok = ok
        self.info = kwargs
        self.info['hostname'] = HOSTNAME
        self.info['time'] = datetime.datetime.now().isoformat()
        self.info['version'] = __version__

    # Remember that __getattr__ is called only as a last resort if the key
    # isn't a normal attr.
    def __getattr__(self, key):
        return self.info.get(key)

    def __bool__(self):
        return self.ok

    def __nonzero__(self):
        return bool(self)

    def __contains__(self, key):
        return key in self.info

    def __str__(self):
        attrs = ["%s=%s" % (key, self.info[key]) for key in sorted(self.info.keys())]
        astr = " ".join(attrs)

        if astr:
            astr = " " + astr

        return "<RichStatus %s%s>" % ("OK" if self else "BAD", astr)

    def toDict(self):
        d = {'ok': self.ok}

        for key in self.info.keys():
            d[key] = self.info[key]

        return d

    @classmethod
    def fromError(self, error, **kwargs):
        kwargs['error'] = error
        return RichStatus(False, **kwargs)

    @classmethod
    def OK(self, **kwargs):
        return RichStatus(True, **kwargs)


def standard_handler(f):
    func_name = getattr(f, '__name__', '<anonymous>')

    @functools.wraps(f)
    def wrapper(*args, **kwds):
        rc = RichStatus.fromError("impossible error")
        session = request.headers.get('x-shakespeare-session', None)
        username = request.headers.get('x-authenticated-as', None)

        logging.debug("%s %s: session %s, username %s, handler %s" %
                      (request.method, request.path, session, username, func_name))

        try:
            rc = f(*args, **kwds)
        except Exception as e:
            logging.exception(e)
            rc = RichStatus.fromError("%s: %s %s failed: %s" % (func_name, request.method, request.path, e))

        code = 200

        # This, candidly, is a bit of a hack.

        if session:
            rc.info['session'] = session

        if username:
            rc.info['username'] = username

        if not rc:
            if 'status_code' in rc:
                code = rc.status_code
            else:
                code = 500

        resp = jsonify(rc.toDict())
        resp.status_code = code

        if session:
            resp.headers['x-shakespeare-session'] = session

        return resp

    return wrapper


######## REST endpoints

####
# GET /health does a basic health check. It always returns a status of 200
# with an empty body.

@app.route("/health", methods=["GET", "HEAD"])
@standard_handler
def health():
    return RichStatus.OK(msg="shakespeare health check OK")


####
# GET /shakespeare/ returns a random quote from the shakespeare_data list of dicts
# as the 'quote' element of a JSON dictionary. It always returns a status of 200.

@app.route("/shakespeare/", methods=["GET"])
@standard_handler
def qd_statement():
    # quote_dict = random.choice(shakespeare_data)
    idx = random.choice(range(len(shakespeare_data)))
    quote_dict = shakespeare_data[idx]
    quote = quote_dict["quote"]
    return RichStatus.OK(idx=idx, quote=quote)


####
# GET /shakespeare/<quoteidx> returns a specific quote. 'quoteid' is the integer index
# of the quote in our array above.
#
# - If all goes well, it returns a JSON dictionary with the requested quote as
#   the 'quote' element, with status 200.
# - If something goes wrong, it returns a JSON dictionary with an explanation
#   of what happened as the 'error' element, with status 400.
#
# PUT /quote/quotenum updates a specific quote. It requires a JSON dictionary
# as the PUT body, with the the new quote contained in the 'quote' dictionary
# element.
#
# - If all goes well, it returns the new quote as if you'd requested it using
#   the GET verb for this endpoint.
# - If something goes wrong, it returns a JSON dictionary with an explanation
#   of what happened as the 'error' element, with status 400.

@app.route("/shakespeare/<int:idx>", methods=["GET", "PUT"])
@standard_handler
def specific_shakespeare(idx):
    if (idx < 0) or (idx >= len(shakespeare_data)):
        return RichStatus.fromError("no quote ID %d" % idx, status_code=400)

    if request.method == "PUT":
        j = request.json

        if (not j) or ('quote' not in j):
            return RichStatus.fromError("must supply 'quote' via JSON dictionary", status_code=400)

        shakespeare_data[idx] = j['quote']

    return RichStatus.OK(idx=idx, quote=shakespeare_data[idx]["quote"])


####
# GET /shakespeare/<quoteidx>/spaketh returns the name of the character who
# spoke the specific quote. 'quoteidx' is the integer index
# of the quote in our array above.
#
# - If all goes well, it returns a JSON dictionary with the requested quote as
#   the 'quote' element, with status 200.
# - If something goes wrong, it returns a JSON dictionary with an explanation
#   of what happened as the 'error' element, with status 400.
#
# PUT /quote/quotenum updates a specific quote. It requires a JSON dictionary
# as the PUT body, with the the new quote contained in the 'quote' dictionary
# element.
#
# - If all goes well, it returns the new quote as if you'd requested it using
#   the GET verb for this endpoint.
# - If something goes wrong, it returns a JSON dictionary with an explanation
#   of what happened as the 'error' element, with status 400.

@app.route("/shakespeare/<int:idx>/spaketh", methods=["GET"])
@standard_handler
def shakespeare_spaketh(idx):
    if (idx < 0) or (idx >= len(shakespeare_data)):
        return RichStatus.fromError("no quote ID %d" % idx, status_code=400)

    quote_dict = shakespeare_data[idx]
    return RichStatus.OK(idx=idx, quote=quote_dict["quote"], spaketh=quote_dict["spaketh"])


@app.route("/shakespeare/<int:idx>/play", methods=["GET"])
@standard_handler
def shakespeare_play(idx):
    if (idx < 0) or (idx >= len(shakespeare_data)):
        return RichStatus.fromError("no quote ID %d" % idx, status_code=400)

    quote_dict = shakespeare_data[idx]
    return RichStatus.OK(idx=idx, quote=quote_dict["quote"], play=quote_dict["play"], verse=quote_dict["verse"])


@app.route("/shakespeare/<int:idx>/iambs", methods=["GET"])
@standard_handler
def shakespeare_iambs(idx):
    if (idx < 0) or (idx >= len(shakespeare_data)):
        return RichStatus.fromError("no quote ID %d" % idx, status_code=400)

    quote_dict = shakespeare_data[idx]
    return RichStatus.OK(idx=idx, quote=quote_dict["quote"], iambs=quote_dict["iambs"])


####
# GET / returns a random quote as the 'quote' element of a JSON dictionary. It
# always returns a status of 200.

@app.route("/", methods=["GET"])
@standard_handler
def statement():
    # XXX time.sleep(0.5)
    return RichStatus.OK(quote=random.choice(quotes))


####
# GET /quote/quoteid returns a specific quote. 'quoteid' is the integer index
# of the quote in our array above.
#
# - If all goes well, it returns a JSON dictionary with the requested quote as
#   the 'quote' element, with status 200.
# - If something goes wrong, it returns a JSON dictionary with an explanation
#   of what happened as the 'error' element, with status 400.
#
# PUT /quote/quotenum updates a specific quote. It requires a JSON dictionary
# as the PUT body, with the the new quote contained in the 'quote' dictionary
# element.
#
# - If all goes well, it returns the new quote as if you'd requested it using
#   the GET verb for this endpoint.
# - If something goes wrong, it returns a JSON dictionary with an explanation
#   of what happened as the 'error' element, with status 400.

@app.route("/quote/<idx>", methods=["GET", "PUT"])
@standard_handler
def specific_quote(idx):
    try:
        idx = int(idx)
    except ValueError:
        return RichStatus.fromError("quote IDs must be numbers", status_code=400)

    if (idx < 0) or (idx >= len(quotes)):
        return RichStatus.fromError("no quote ID %d" % idx, status_code=400)

    if request.method == "PUT":
        j = request.json

        if (not j) or ('quote' not in j):
            return RichStatus.fromError("must supply 'quote' via JSON dictionary", status_code=400)

        quotes[idx] = j['quote']

    return RichStatus.OK(quote=quotes[idx])


####
# POST /quote adds a new quote to our list. It requires a JSON dictionary
# as the POST body, with the the new quote contained in the 'quote' dictionary
# element.
#
# - If all goes well, it returns a JSON dictionary with the new quote's ID as
#   'quoteid', and the new quote as 'quote', with a status of 200.
# - If something goes wrong, it returns a JSON dictionary with an explanation
#   of what happened as the 'error' element, with status 400.

@app.route("/quote", methods=["POST"])
@standard_handler
def new_quote():
    j = request.json

    if (not j) or ('quote' not in j):
        return RichStatus.fromError("must supply 'quote' via JSON dictionary", status_code=400)

    quotes.append(j['quote'])

    idx = len(quotes) - 1

    return RichStatus.OK(quote=quotes[idx], quoteid=idx)


@app.route("/crash", methods=["GET"])
@standard_handler
def crash():
    logging.warning("dying in 1 seconds")
    time.sleep(1)
    os.kill(os.getpid(), signal.SIGTERM)
    time.sleep(1)
    os.kill(os.getpid(), signal.SIGKILL)


######## Mainline

def main():
    app.run(debug=True, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    logging.basicConfig(
        # filename=logPath,
        level=logging.DEBUG,  # if appDebug else logging.INFO,
        format="%%(asctime)s shakespeare %s %%(levelname)s: %%(message)s" % __version__,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logging.info("initializing on %s:%d" % (HOSTNAME, PORT))
    main()

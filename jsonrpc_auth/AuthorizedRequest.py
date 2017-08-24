""" Implements generating an authorised JSON-RPC request using a particular private key in WIF format
"""
import steem
from steem.account import Account
import json
import hashlib
import collections
import secp256k1

from binascii import hexlify,unhexlify
from steembase.base58 import Base58, base58decode

from jsonrpcclient.request import Request

import secp256k1

def canon_params(params):
    """ Ensures the params are canon
    """
    if type(params) is list:
       return [canon_params(param) for param in params]
    elif type(params) is dict:
       param_names = sorted(params.keys())
       retval = collections.OrderedDict()
       for k in param_names:
           v = params[k]
           if type(params[k]) is dict: v = canon_params(params[k])
           retval[k] = v
       return retval
    else:
       return params

def canon_request(request):
    """ Turns a request into a canon request
    """
    if 'params' in request.keys():
       request['params'] = canon_params(request['params'])
    json_req = json.dumps(request)
    return json_req

def get_ecdsa_pubkey(wif):
    """ Takes a key in WIF format and returns an ECDSA public key that can be used to verify signatures
    """
    pub_key   = Base58('STM5sWzsUCociNCxaRJhQ1WKyZVBduDUy7uR4yrifX9vLhh9LxeKv')
    ecdsa_pub = secp256k1.PublicKey(bytes(pub_key),raw=True)
    return ecdsa_pub

def sign_request(request,wif):
    """ Signs a request with the provided WIF
        Request will first be made canon and JSON-encoded

        Return value will be a tuple of (json_request,authsig)
    """
    canon_req  = canon_request(request)
    digest     = hashlib.sha256(canon_req.encode('utf-8')).digest()
    priv_key   = Base58(wif)
    ecdsa_priv = secp256k1.PrivateKey(bytes(priv_key),raw=True)
    sig        = ecdsa_priv.ecdsa_sign(digest,raw=True)
    hex_sig    = hexlify(ecdsa_priv.ecdsa_serialize(sig)).decode('utf-8')
    request['params']['AuthSig'] = hex_sig
    request['params']['AuthKey'] = wif
    canon_req = canon_request(request)
    return (canon_req,hex_sig,wif)

def verify_request_with_pub(request,pub_key,hex_sig):
    """ Verifies a request (in JSON format) was signed in a valid way
        Returns either True or False
    """
    request   = json.loads(canon_request(json.loads(request)))

    del request['params']['AuthSig']
    del request['params']['AuthKey']

    request   = json.dumps(request)
    digest    = hashlib.sha256(request.encode('utf-8')).digest()
    pub_key   = Base58(pub_key)
    ecdsa_pub = secp256k1.PublicKey(bytes(pub_key),raw=True)
    ecdsa_sig = ecdsa_pub.ecdsa_deserialize(unhexlify(hex_sig))
    return ecdsa_pub.ecdsa_verify(digest,ecdsa_sig,raw=True)

def verify_request(request,username):
    """ Verifies a request (not in JSON format) against a user account in the steem blockchain
    """
    if not 'AuthKey' in request['params'].keys(): return False
    if not 'AuthSig' in request['params'].keys(): return False
    user_account = Account(username)
    posting_keys = []
    for key in user_account: posting_keys.append(key[0])
    if not request['params']['AuthKey'] in posting_keys: return False
    return verify_request_with_pub(json.dumps(request),request['params']['AuthKey'],request['params']['AuthSig'])

if __name__=='__main__':
   pub_key  = 'STM5sWzsUCociNCxaRJhQ1WKyZVBduDUy7uR4yrifX9vLhh9LxeKv'
   priv_key = '5JxQDXSZNBLLTMqMFMGswdCnwn5KWdFv6NVSBEJTLEg1v5gvU9b'

   request  = Request('update_preferences',test_pref=1,details={'username':'testuser','prefer_ssl':True})
   print('Signing request %s with private key %s' % (str(request),priv_key))
   canon_req,hex_sig,wif = sign_request(request,priv_key)

   print('Got canon request: %s' % canon_req)
   print('Got auth signature: %s' % hex_sig)

   print('Verifying request with public key %s' % pub_key)
   verified = verify_request_with_pub(canon_req,pub_key,hex_sig)

   print('Verified: %s' % str(verified))

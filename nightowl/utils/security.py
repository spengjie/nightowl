import base64
import hashlib
import re
import string
from binascii import hexlify
from secrets import choice

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA

from nightowl.config import security_config


def base64url_encode(input):
    if isinstance(input, str):
        input = input.encode()
    output = base64.urlsafe_b64encode(input).replace(b'=', b'')
    return output.decode()


def base64url_decode(input):
    if isinstance(input, str):
        input = input.encode()

    rem = len(input) % 4

    if rem > 0:
        input += b'=' * (4 - rem)
    output = base64.urlsafe_b64decode(input)
    return output.decode()


def random(length=8, chars=string.ascii_letters+string.digits):
    return ''.join([choice(chars) for i in range(length)])


def sha256(data, salt=None):
    if isinstance(data, str):
        data = data.encode()
    if salt:
        if isinstance(salt, str):
            salt = salt.encode()
        data = salt + b':' + data
    return hashlib.sha256(data).hexdigest()


def encrypt(data, salt=None, urlsafe=False):
    if isinstance(data, str):
        data = data.encode()
    if salt:
        if isinstance(salt, str):
            salt = salt.encode()
        data = salt + b':' + data
    key = security_config.aes_key.encode()
    iv = hexlify(security_config.aes_iv.encode())
    encipher = AES.new(key, AES.MODE_CFB, iv)
    if urlsafe:
        b64 = base64.urlsafe_b64encode
    else:
        b64 = base64.b64encode
    return b64(encipher.encrypt(data)).decode()


def decrypt(encrypted, salt=None, urlsafe=False):
    if isinstance(encrypted, str):
        encrypted = encrypted.encode()
    key = security_config.aes_key.encode()
    iv = hexlify(security_config.aes_iv.encode())
    decipher = AES.new(key, AES.MODE_CFB, iv)
    if urlsafe:
        b64 = base64.urlsafe_b64decode
    else:
        b64 = base64.b64decode
    decrypted = decipher.decrypt(b64(encrypted))
    if salt:
        decrypted = decrypted[len(salt)+1:]
    return decrypted.decode()


def rsa_encrypt(data, salt=None, urlsafe=False):
    if not data:
        return data
    if isinstance(data, str):
        data = data.encode()
    if salt:
        if isinstance(salt, str):
            salt = salt.encode()
        data = salt + b':' + data
    key = security_config.rsa_private_key.encode()
    passphrase = security_config.rsa_private_key_passphrase
    encipher = PKCS1_v1_5.new(RSA.importKey(key, passphrase))
    if urlsafe:
        b64 = base64.urlsafe_b64encode
    else:
        b64 = base64.b64encode
    return b64(encipher.encrypt(data)).decode()


def rsa_decrypt(encrypted, salt=None, urlsafe=False):
    if not encrypted:
        return encrypted
    if isinstance(encrypted, str):
        encrypted = encrypted.encode()
    key = security_config.rsa_private_key.encode()
    passphrase = security_config.rsa_private_key_passphrase
    decipher = PKCS1_v1_5.new(RSA.importKey(key, passphrase))
    if urlsafe:
        b64 = base64.urlsafe_b64decode
    else:
        b64 = base64.b64decode
    decrypted = decipher.decrypt(b64(encrypted), None)
    if salt:
        decrypted = decrypted[len(salt)+1:]
    return decrypted.decode()


def weak_password(password, length=12):
    message = f'Your password must have {length} or more characters ' \
        'and include at least 3 kinds of the following characters: \n' \
        ' 1. uppercase letter\n' \
        ' 2. lowercase letter\n' \
        ' 3. number\n' \
        ' 4. special character'
    if len(password) < length:
        return message
    matched_num = 0
    if re.search(r'[A-Z]', password):
        matched_num += 1
    if re.search(r'[a-z]', password):
        matched_num += 1
    if re.search(r'\d', password):
        matched_num += 1
    if re.search(r'[!"#$%&\\\'()*+,-./:;<=>?@[\]^_`{|}~]', password):
        matched_num += 1
    if matched_num < 3:
        return message
    return ''

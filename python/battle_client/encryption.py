import base64
import hashlib

from Crypto.Cipher import AES

CRABADA_AES_KEY = 'uPrwNC7WZr9vEYMGv1pnkeQuogTY8t6P'.encode('utf-8')
CRABADA_AES_IV = 'BJcmqPomKAYdbfIi'.encode('utf-8')


def crabada_checksum(plain_text: str) -> str:
    """Creates a text string used in the Hash header value from the body of the request."""
    # Encryptor must be generated fresh each time.
    encryptor = AES.new(CRABADA_AES_KEY, AES.MODE_CBC, CRABADA_AES_IV)
    # Text must be padded for use with CBC.
    padded_text = pad_for_cbc(plain_text, encryptor.block_size)
    # Encrypt dat.
    encrypted_text = encryptor.encrypt(padded_text.encode('utf-8'))
    # Then convert to base64 for some reason.
    base64_text = base64.b64encode(encrypted_text)
    # Then MD5 it.
    md5_text = hashlib.md5(base64_text)
    # Result is the MD5 hash with all uppercase letters.
    return md5_text.hexdigest().upper()


def pad_for_cbc(s: str, bs: int) -> str:
    """Prep plaintext for AES processing in CBC mode."""
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)


if __name__ == '__main__':
    tests = {
        '85D0A85153A24B68C6C217BEEB5903FC': '{"achievement_id":20}',
        # Other tests removed since they have PII. Feel free to add your own.
    }
    for expected_output, known_input in tests.items():
        print('input:', known_input)
        print('want:', expected_output)
        print('got :', crabada_checksum(known_input))
        print()

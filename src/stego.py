import argparse
import hashlib
import sys

import numpy as np
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
PBKDF2_ITERS = 200_000


# работа с картинкой

def load_image(path):
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.uint8)


def save_image(arr, path):
    Image.fromarray(arr).save(path, format="PNG")


# байты <-> биты

def bytes_to_bits(data):
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_bytes(bits):
    return np.packbits(bits).tobytes()


# порядок позиций

def get_positions(n, password=None):
    if password is None:
        return np.arange(n)
    seed = int.from_bytes(hashlib.sha256(("positions:" + password).encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    return rng.permutation(n)


# сам LSB

def embed_bytes(cover, data, password=None):
    payload = len(data).to_bytes(4, "big") + data
    bits = bytes_to_bits(payload)

    flat = cover.reshape(-1).copy()
    capacity = flat.size
    if len(bits) > capacity:
        raise ValueError(
            f"Сообщение не помещается: нужно {len(bits)} бит, "
            f"а в картинке есть только {capacity} бит"
        )

    pos = get_positions(capacity, password)[:len(bits)]
    flat[pos] = (flat[pos] & 0xFE) | bits
    return flat.reshape(cover.shape)


def extract_bytes(stego, password=None):
    flat = stego.reshape(-1)
    pos = get_positions(flat.size, password)

    length = int.from_bytes(bits_to_bytes(flat[pos[:32]] & 1), "big")
    if 32 + length * 8 > flat.size:
        raise ValueError("Неправильная длина в заголовке (не тот режим или пароль?)")

    bits = flat[pos[32:32 + length * 8]] & 1
    return bits_to_bytes(bits)


# шифрование

def encrypt(text_bytes, password):
    salt = get_random_bytes(SALT_LEN)
    nonce = get_random_bytes(NONCE_LEN)
    key = PBKDF2(password, salt, 32, count=PBKDF2_ITERS, hmac_hash_module=SHA256)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(text_bytes)
    return salt + nonce + tag + ct


def decrypt(blob, password):
    salt = blob[:SALT_LEN]
    nonce = blob[SALT_LEN:SALT_LEN + NONCE_LEN]
    tag = blob[SALT_LEN + NONCE_LEN:SALT_LEN + NONCE_LEN + TAG_LEN]
    ct = blob[SALT_LEN + NONCE_LEN + TAG_LEN:]
    key = PBKDF2(password, salt, 32, count=PBKDF2_ITERS, hmac_hash_module=SHA256)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ct, tag)


# три режима

def hide(cover, message_bytes, mode, password=None):
    if mode == "plain":
        return embed_bytes(cover, message_bytes)
    if password is None:
        raise ValueError("Для режимов encrypted и random нужен пароль")
    blob = encrypt(message_bytes, password)
    if mode == "encrypted":
        return embed_bytes(cover, blob)
    if mode == "random":
        return embed_bytes(cover, blob, password)
    raise ValueError("Неизвестный режим: " + mode)


def reveal(stego, mode, password=None):
    if mode == "plain":
        return extract_bytes(stego)
    if password is None:
        raise ValueError("Для режимов encrypted и random нужен пароль")
    if mode == "encrypted":
        blob = extract_bytes(stego)
    elif mode == "random":
        blob = extract_bytes(stego, password)
    else:
        raise ValueError("Неизвестный режим: " + mode)
    return decrypt(blob, password)


# командная строка

def main():
    parser = argparse.ArgumentParser(description="LSB-стеганография (+ AES-GCM)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("embed", help="спрятать сообщение")
    e.add_argument("-i", "--input", required=True, help="исходная картинка")
    e.add_argument("-o", "--output", required=True, help="куда сохранить stego.png")
    e.add_argument("-m", "--message", help="текст сообщения")
    e.add_argument("-f", "--file", help="или файл с текстом")
    e.add_argument("--mode", choices=["plain", "encrypted", "random"], default="plain")
    e.add_argument("-p", "--password")

    x = sub.add_parser("extract", help="достать сообщение")
    x.add_argument("-i", "--input", required=True, help="stego-картинка")
    x.add_argument("-o", "--output", help="сохранить текст в файл")
    x.add_argument("--mode", choices=["plain", "encrypted", "random"], default="plain")
    x.add_argument("-p", "--password")

    args = parser.parse_args()

    try:
        if args.cmd == "embed":
            if args.file:
                with open(args.file, "rb") as f:
                    data = f.read()
            elif args.message is not None:
                data = args.message.encode("utf-8")
            else:
                raise ValueError("Нужно указать -m или -f")
            stego = hide(load_image(args.input), data, args.mode, args.password)
            save_image(stego, args.output)
            print(f"Готово: {args.output} ({len(data)} байт, режим {args.mode})")
        else:
            data = reveal(load_image(args.input), args.mode, args.password)
            if args.output:
                with open(args.output, "wb") as f:
                    f.write(data)
                print(f"Сообщение сохранено в {args.output}")
            else:
                print(data.decode("utf-8", errors="replace"))
    except (ValueError, FileNotFoundError) as err:
        print("Ошибка:", err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

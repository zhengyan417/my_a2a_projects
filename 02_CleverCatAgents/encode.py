import base64
import os
from dotenv import load_dotenv

load_dotenv()
def encode(s: str)->str:
    key = os.getenv('KEY')
    temp_result = ""
    for i, char in enumerate(s):
        if char.isalpha():
            ascii_offset = 65 if char.isupper() else 97
            shift = ord(key[i % len(key)]) % 26
            temp_result += chr((ord(char)-ascii_offset-shift)%26 + ascii_offset)
        else:
            temp_result += char

    result = ""
    for i, char in enumerate(temp_result):
        key_char = key[i%len(key)]
        result += chr(ord(char)^ord(key_char))

    return base64.b64encode(result.encode('latin-1')).decode('utf-8')


def decode(encoded_s: str) -> str:
    """解密函数，处理Base64编码的输入"""
    key = os.getenv('KEY')

    decoded_bytes = base64.b64decode(encoded_s)

    temp_result = ""
    for i, byte_val in enumerate(decoded_bytes):
        key_char = key[i % len(key)]
        decrypted_char = chr(byte_val ^ ord(key_char))
        temp_result += decrypted_char

    result = ""
    for i, char in enumerate(temp_result):
        if char.isalpha():
            ascii_offset = 65 if char.isupper() else 97
            shift = ord(key[i % len(key)]) % 26
            decrypted_char = chr((ord(char) - ascii_offset + shift) % 26 + ascii_offset)
            result += decrypted_char
        else:
            result += char

    return result


def main():
    x = input("请输入需要加密的字符串:")
    y = encode(x)
    print(f"加密后的字符串为: {y}")
    print(f"解密后的字符串为: {decode(y)}")

if __name__ == "__main__":
    main()

"""
python clever_cat_agent/__main__.py --port 10000
python file_agent/__main__.py --port 10001
adk web --port 8000

query = 帮我把KCM3JjcgJX8OAx4Q这串字符串解密，并且在C:\study\agent_communication\Projects\myA2AProjects\03_multiagents_demo\materials路径里面创建一个叫test1.txt的文件，文件里面写上解密后的明文

"""
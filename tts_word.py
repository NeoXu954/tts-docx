import websocket
import json
import os
import _thread as thread
import ssl
from docx import Document
import requests
import base64
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime
from time import mktime
from pydub import AudioSegment
from wsgiref.handlers import format_date_time

class Ws_Param(object):
    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text
        self.CommonArgs = {"app_id": self.APPID}
        self.BusinessArgs = {"aue": "raw", "auf": "audio/L16;rate=16000", "vcn": "x4_lingxiaolu_en", "tte": "utf8"}
        # 确保文本内容正确编码为 Base64
        self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}


    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        url = url + '?' + urlencode(v)
        return url

def read_text_from_word(file_path):
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def upload_file(file_path):
    upload_url = 'http://127.0.0.1:5000/upload'
    with open(file_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(upload_url, files=files)

    if response.status_code == 200:
        return response.json().get('file_url')
    else:
        raise Exception(f"File upload failed with status code {response.status_code}")

def on_message(ws, message):
    try:
        message = json.loads(message)
        print(message)  # 输出整个消息以便调试

        if "data" in message and "audio" in message["data"]:
            audio = base64.b64decode(message["data"]["audio"])
            with open('./demo.pcm', 'ab') as f:
                f.write(audio)
        elif "code" in message and message["code"] != 0:
            print("Error code:", message["code"])
            print("Error message:", message["message"])

    except Exception as e:
        print("Receive msg, but parse exception:", e)

def on_error(ws, error):
    print("### error:", error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")
    print(f"Status code: {close_status_code}, Message: {close_msg}")


def on_open(ws):
    def run(*args):
        text_file_path = 'D:/下载/tts_ws_python3_demo/tts_ws_python3_demo/tts_ws_python3_demo/conference.docx'
        text_content = read_text_from_word(text_file_path)

        # 确保文本内容正常
        print("Text content:", text_content)

        d = {"common": wsParam.CommonArgs,
             "business": wsParam.BusinessArgs,
             "data": {"status": 2, "text": str(base64.b64encode(text_content.encode('utf-8')), "UTF8")},
             }
        d = json.dumps(d)
        print("------>开始发送文本数据")
        ws.send(d)

    thread.start_new_thread(run, ())


def convert_pcm_to_wav(pcm_file, wav_file):
    # 确保音频文件每次处理时都是新的
    audio = AudioSegment.from_file(pcm_file, format="raw", frame_rate=16000, channels=1, sample_width=2)
    audio.export(wav_file, format="wav")
    print(f"音频已保存为: {wav_file}")


if __name__ == "__main__":
    wsParam = Ws_Param(APPID='618dc58b', APISecret='Y2IyNmY2NWRiYmEwM2JjMWMyYjFlODQ1',
                       APIKey='d06f53d1c5c450435ae01d2c6791a3eb',
                       Text="")
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    convert_pcm_to_wav('./demo.pcm', './output.wav')

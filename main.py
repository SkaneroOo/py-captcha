import random
from enum import Enum
from time import time_ns
from uuid import uuid4, UUID
from asyncio import sleep
from io import BytesIO
from string import ascii_letters, digits
char_list = ascii_letters + digits

import cv2 as cv
import numpy as np
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse

# print(cv.FONT_HERSHEY_COMPLEX)
# print(cv.FONT_HERSHEY_COMPLEX_SMALL)
# print(cv.FONT_HERSHEY_DUPLEX)
# print(cv.FONT_HERSHEY_PLAIN)
# print(cv.FONT_HERSHEY_SIMPLEX)
# print(cv.FONT_HERSHEY_TRIPLEX)


class CaptchaType(Enum):
    TEXT = 0
    NUMBER = 1


class Captcha:
    captcha_value: str | int
    captcha_type: CaptchaType
    
    
    def __init__(self, c_type: CaptchaType):
        self.captcha_type = c_type
        if c_type == CaptchaType.TEXT:
            self.captcha_value = self._get_text_captcha()
        elif c_type == CaptchaType.NUMBER:
            self.captcha_value = self._get_number_captcha()
            
    
    def _get_text_captcha(self) -> str:
        return "".join([random.choice(char_list) for _ in range(random.randint(6, 8))])
    
    def _get_number_captcha(self) -> int:
        return -1                       # not implemented


class CaptchaCore(FastAPI):
    
    captchas: dict[str, Captcha]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.captchas = dict()
        self.add_api_route("/", self.index, methods=["GET"])
        self.add_api_route("/request", self.request_text_captcha, methods=["GET"])
        self.add_api_route("/captcha/{uuid}", self.get_captcha, methods=["GET"])
        self.add_api_route("/captchaimage/{uuid}", self.get_captcha_image, methods=["GET"])
        self.add_api_route("/verify/{uuid}/{text}", self.verify_captcha, methods=["GET"])
        
    
    async def index(self):
        return HTMLResponse(open("index.html", "r").read())
        
    
    async def verify_captcha(self, uuid: str, text: str):
        if not uuid in self.captchas:
            return JSONResponse({"Error": "Captcha ID invalid", "success": False}, status_code=404)
        if self.captchas[uuid].captcha_value == text:
            return JSONResponse({"success": True})
        return JSONResponse({"success": False})
    
    async def request_text_captcha(self, bg_tasks: BackgroundTasks):
        uuid = str(uuid4())
        self.captchas[uuid] = Captcha(CaptchaType.TEXT)
        bg_tasks.add_task(self.remove_captcha, uuid=uuid)
        return JSONResponse({"captcha_id": uuid})
        
        
    async def get_captcha(self, uuid: str):
        if uuid in self.captchas:
            return JSONResponse({"captcha_id": uuid, "captcha_value": self.captchas[uuid].captcha_value})
        return JSONResponse({"Error": "Captcha ID invalid"}, status_code=404)
    
    
    async def get_captcha_image(self, uuid: str):
        if not uuid in self.captchas:
            return JSONResponse({"Error": "Captcha ID invalid"}, status_code=404)
        captcha = self.captchas[uuid]
        canvas = np.zeros([160, 480, 3], dtype=np.uint8)
        canvas[::] = 255
        
        spacing = 420//len(captcha.captcha_value)
        for i, c in enumerate(captcha.captcha_value):
            cv.putText(
                canvas, 
                c, 
                (40+random.randint(-15, 15)+spacing*i, 100+random.randint(-30, 30)), 
                random.randint(0, 7), 
                2, 
                (random.randint(0, 127), random.randint(0, 127), random.randint(0, 127)),
                2
            )
        
        for _ in range(random.randint(2, 5)):
            cv.line(canvas, (random.randint(0, 479), random.randint(0, 159)),
                    (random.randint(0, 479), random.randint(0, 159)),
                    (random.randint(0, 63), random.randint(0, 63), random.randint(0, 63)),
                    random.randint(1, 2))
        
        _, img = cv.imencode(".png", canvas)
        buffer = BytesIO(img)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="image/png")
        
        
    async def remove_captcha(self, uuid: str):
        await sleep(300)
        if uuid in self.captchas:
            self.captchas.pop(uuid)
            
app = CaptchaCore()

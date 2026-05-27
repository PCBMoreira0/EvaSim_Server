from fastapi import APIRouter
from concurrent.futures import ThreadPoolExecutor
import hashlib
from io import BytesIO
import os
import speech_recognition
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from pydantic import BaseModel

import asyncio
from fastapi.responses import FileResponse, StreamingResponse
from fastapi import HTTPException, UploadFile

router = APIRouter(tags=["API"])

# Função para configurar o serviço TTS
def configure_tts():
    try:
        # Lê as credenciais do arquivo
        with open("ibm_cred.txt", "r") as ibm_cred:
            ibm_config = ibm_cred.read().splitlines()

        apikey = ibm_config[0]
        url = ibm_config[1]

        # Configuração do autenticador e do serviço
        authenticator = IAMAuthenticator(apikey)
        tts = TextToSpeechV1(authenticator=authenticator)
        tts.set_service_url(url)
        return tts
    except:
        print("ERROR setting TTS")
        return None

# Agora você pode chamar essa função para obter o objeto tts em qualquer parte do código
tts = configure_tts()

class InputModel(BaseModel):
    input : str

executor = ThreadPoolExecutor(max_workers=4)

# API routes

@router.get("/audio/{name}", response_class=FileResponse)
def get_audio(name : str):
    audio_path= "audio_files/" + name + ".wav"
    if os.path.exists(audio_path):
        return FileResponse(audio_path, media_type="audio/wav")
    else:
        raise HTTPException(status_code=404, detail="File not found")



def process_stt(file):
    r = speech_recognition.Recognizer()

    audio_data = BytesIO(file)

    with speech_recognition.AudioFile(audio_data) as source:
        audio = r.record(source)

    # recognize speech using Google Speech Recognition
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)` 
        result = r.recognize_google(audio, language="pt-BR")
        if result is None: 
            return {"error":"Could not transcribe the audio"}
        return {"result":result}
    except speech_recognition.UnknownValueError:
        {"error":"Google Speech Recognition could not understand audio"}
    except speech_recognition.RequestError as e:
        {"error":"Could not request results from Google Speech Recognition service; {0}".format(e)}


#STT
@router.post("/stt")
async def get_stt(file : UploadFile):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_stt, await file.read())
    print("STT: " + result["result"])
    return result

#user emotion
@router.post("/emotion")
async def get_emotion(file : UploadFile):
    import emotion
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, emotion.run_from_image, await file.read())
    
    return {"result": result}


# TTS Watson
@router.post("/tts")
async def get_tts_watson(input : InputModel):
    hash_object = hashlib.md5(input.input.encode())
    tone_voice = "pt-BR_IsabelaV3Voice"
    file_name = "_audio_"  + tone_voice + hash_object.hexdigest()
    
    if (os.path.isfile("audio_cache_files/" + file_name + ".mp3")):
        audio_path = "audio_cache_files/" + file_name + ".mp3"
        audio = open(audio_path, "rb")
        return StreamingResponse(audio, media_type="audio/mpeg")
    else:
        audio_file_is_ok = False
        while(not audio_file_is_ok):
            # Eva TTS functions
            audio_ext = ".mp3"
            ibm_audio_ext = "audio/mp3"
            with open("audio_cache_files/" + file_name + audio_ext, 'wb') as audio_file:
                try:
                    res = tts.synthesize(input.input, accept = ibm_audio_ext, voice = tone_voice).get_result()
                    audio_file.write(res.content)
                    audio_path = "audio_cache_files/" + file_name + ".mp3"
                    audio = open(audio_path, "rb")
                    return StreamingResponse(audio, media_type="audio/mpeg")
                    # self.playsound("audio_cache_files/" + file_name + audio_ext, block = True) # self.play the audio of the speech
                except:
                    print("Voice exception")
                    print("\nError when trying to select voice tone, please verify the tone atribute.\n", "error")
                    return {"error":"Error when trying to select voice tone, please verify the tone atribute."}
                
            file_size = os.path.getsize("audio_cache_files/" + file_name + self.audio_ext)
            if file_size == 0: # Corrupted file
                print("#### Corrupted file.. (It's necessary to use the same implementation like in tts-module in EVA robot!)")
                os.remove("audio_cache_files/" + file_name + self.audio_ext)
            else:
                audio_file_is_ok = True
    
    
    raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado.")
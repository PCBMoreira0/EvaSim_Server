class MqttJsonConverter:
    @staticmethod
    def mqtt_to_json(topic : str, payload : str) -> dict:
        command = topic.split("/")[-1]
        if command == "TALK":
            return {
                "command": "talk",
                "parameter": {"text": payload}
            }
        
        elif command == "LISTEN":
            return {
                "command": "listen",
                "parameter": {"request": payload}
            }
        elif command == "AUDIO":
            parameter = payload.split("|")
            
            return {
                "command": "audio",
                "parameter": {"audio":parameter[0], "block":parameter[1].lower() == "true"}
            }
        elif command == "LEDS":
            return {
                "command": "leds",
                "parameter": {"state": payload}
            }
        elif command == "EVAEMOTION":
            return {
                "command": "emotion",
                "parameter": {"type": payload}
            }
        elif command == "LIGHT":
            parameter = payload.split("|")

            return {
                "command": "light",
                "parameter": {"color":parameter[0], "state":parameter[1]}
            }
        elif command == "MOTION":
            return {
                "command": "motion",
                "parameter": {"head":payload}
            }
        elif command == "QRREAD":
            return {
                "command":"qrread",
                "parameter": {"request":"SERVICE_REQUEST"}
            }
        elif command == "WAIT":
            return {
                "command":"wait",
                "parameter":{"duration":int(payload)}
            }
        elif command == "USEREMOTION":
            return {
                "command":"useremotion",
                "parameter": {"request":"SERVICE_REQUEST"}
            }
        elif command == "END_SCRIPT":
            return {
                "command":"end_script",
                "parameter":{}
            }
        elif command == "ERROR":
            parameter = payload.split("|")
            return {
                "command":"error",
                "parameter":{"type":parameter[0], "description":parameter[1]}
            }
        
    @staticmethod
    def json_to_mqtt(json_message : dict) -> tuple[str, str]:
        command = json_message["command"]
        topic = ""
        if command == "talk_response":
            topic = "TALK_RESPONSE"
        elif command == "listen_response":
            topic = "LISTEN_RESPONSE"
        elif command == "audio_response":
            topic = "AUDIO_RESPONSE"
        elif command == "qrread_response":
            topic = "QRREAD_RESPONSE"
        elif command == "useremotion_response":
            topic = "USEREMOTION_RESPONSE"
        elif command == "start":
            topic = "START"
        elif command == "set_script":
            topic = "SET_SCRIPT"
        elif command == "kill":
            topic = "KILL"
        elif command == "reset":
            topic = "RESET"
        
        payload = json_message["parameter"]
        return topic, payload
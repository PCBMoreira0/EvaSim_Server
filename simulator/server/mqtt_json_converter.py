class MqttJsonConverter:
    @staticmethod
    def mqtt_to_json(topic : str, payload : str) -> dict:
        command = topic.split("/")[-1]
        if command == "TALK":
            return {
                "command": "talk",
                "parameter": payload
            }
        
        elif command == "LISTEN":
            return {
                "command": "listen",
                "parameter": payload
            }
        elif command == "AUDIO":
            parameter = payload.split("|")
            
            return {
                "command": "audio",
                "parameter": [{"audio":parameter[0]}, {"block":parameter[1]}]
            }
        elif command == "LED":
            return {
                "command": "led",
                "parameter": payload
            }
        elif command == "EVAEMOTION":
            return {
                "command": "emotion",
                "parameter": payload
            }
        elif command == "LIGHT":
            parameter = payload.split("|")

            return {
                "command": "light",
                "parameter": [{"color":parameter[0]}, {"state":parameter[1]}]
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
        
        payload = json_message["parameter"]
        return topic, payload
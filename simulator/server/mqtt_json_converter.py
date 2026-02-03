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
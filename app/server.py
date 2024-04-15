#!/usr/bin/env python3
import argparse
import io
import logging
import wave
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, request

from urllib.parse import parse_qs

from piper.voice import PiperVoice
from piper.download import ensure_voice_exists, find_voice, get_voices

_LOGGER = logging.getLogger()
# TODO: differnt path than ./ does currently not work
DATA_DIR = "./"
HOST = "0.0.0.0"
PORT = 59125

class ServerApp():
    def __init__(self, default_voice: str) -> None:
        self._voices = get_voices(DATA_DIR, update_voices=True)
    
    def voices(self) -> List[str]:
        return self._voices


def main() -> None:
    server_app = ServerApp("en_US-lessac-medium")

    # Create web server
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def app_synthesize() -> bytes:
        if request.method == "POST":
            text = request.data.decode("utf-8")
        else:
            text = request.args.get("text", "")

        text = text.strip()
        if not text:
            raise ValueError("No text provided")

        _LOGGER.debug("Synthesizing text: %s", text)
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, "wb") as wav_file:
                #voice.synthesize(text, wav_file, **synthesize_args)
                pass

            return wav_io.getvalue()

    @app.route("/voices", methods=["GET"])
    def voices():
        lines = []
        voices = server_app.voices()
        for voice_name in voices:
            voice = voices[voice_name]
            num_speakers = voice["num_speakers"]
            language_code = voice["language"]["code"]
            if num_speakers > 1:
                speaker_map = voice["speaker_id_map"]
                for speaker in speaker_map:
                    line = f"{voice_name}:{speaker} {language_code} NA VITS"
                    lines.append(line)
                print(voice)
            else:
                line = f"{voice_name} {language_code} NA VITS"
                lines.append(line)
        lines.sort()
        return "\n".join(lines)

    @app.route("/process", methods=["GET", "POST"])
    def api_marytts_process():
        """MaryTTS-compatible /process endpoint"""
        voices_info = server_app.voices()
        voice_name = "NO VOICE SELECTED"
        speaker_id = None
        if request.method == "POST":
            data = parse_qs(request.data.decode())
            text = data.get("INPUT_TEXT", [""])[0]

            if "VOICE" in data:
                voice_name = str(data.get("VOICE", [voice_name])[0]).strip()
        else:
            text = request.args.get("INPUT_TEXT", "")
            voice_name = str(request.args.get("VOICE", voice_name)).strip()

        if ":" in voice_name:
            speaker_name = voice_name[voice_name.find(":")+1:]
            
            voice_name = voice_name[:voice_name.find(":")]
            print(voices_info[voice_name])
            speaker_id = voices_info[voice_name]["speaker_id_map"][speaker_name]
        print(voice_name)
        print(speaker_id)
        print(text)
        
        ensure_voice_exists(voice_name, [DATA_DIR], DATA_DIR, voices_info)
        voice = PiperVoice.load(f"{voice_name}.onnx", config_path=None, use_cuda=False)
        
        synthesize_args = {
            "speaker_id": speaker_id,
            "length_scale": None,
            "noise_scale": None,
            "noise_w": None,
            "sentence_silence": 0.0,
        }
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, "wb") as wav_file:
                voice.synthesize(text, wav_file, **synthesize_args)

            return wav_io.getvalue()

    app.run(host=HOST, port=PORT)


if __name__ == "__main__":
    main()

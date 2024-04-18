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
DEFAULT_VOICE_CACHE_DIR = "./data/"
DEFAULT_VOICE_CUSTOM_DIR = "./custom/"
HOST = "0.0.0.0"
PORT = 59125

class ServerApp():
    def __init__(self, voice_cache_dir: str, voice_custom_dir: str, default_voice: str) -> None:
        self._voice_cache_dir = voice_cache_dir
        self._voice_custom_dir = voice_custom_dir
        self._voices = get_voices(self._voice_cache_dir, update_voices=True)
    
    def _get_voices(self) -> List[str]:
        return self._voices
    
    def mary_voices(self):
        # TODO: add voices from custom folder
        lines = []
        voices = self._voices
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
    
    def mary_process(self, request):
        voices_info = self._get_voices()
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
        try:
            onnx_path, config_path = find_voice(voice_name, [self._voice_cache_dir, self._voice_custom_dir])
        except ValueError:
            ensure_voice_exists(voice_name, [self._voice_cache_dir], self._voice_cache_dir, voices_info)
            onnx_path, config_path = find_voice(voice_name, [self._voice_cache_dir, self._voice_custom_dir])

        voice = PiperVoice.load(onnx_path, config_path=None, use_cuda=False)
        
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Mary Piper TTS Web API")
    
    # Argument for cache directory
    parser.add_argument('--cache-dir', dest='cache_dir', type=str, default=DEFAULT_VOICE_CACHE_DIR,
                        help='Directory for caching voices that are downloaded')

    # Argument for voice directory
    parser.add_argument('--custom-voice-dir', dest='custom_voice_dir', type=str, default=DEFAULT_VOICE_CUSTOM_DIR,
                        help='Directory for custom voices')

    args = parser.parse_args()

    # Using the provided or default directories
    voice_cache_dir = args.cache_dir
    voice_custom_dir = args.custom_voice_dir

    print("Cache directory:", voice_cache_dir)
    print("Voice directory:", voice_custom_dir)
    
    server_app = ServerApp(voice_cache_dir, voice_custom_dir, "en_US-lessac-medium")

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
        return server_app.mary_voices()

    @app.route("/process", methods=["GET", "POST"])
    def api_marytts_process():
        """MaryTTS-compatible /process endpoint"""
        return server_app.mary_process(request)

    app.run(host=HOST, port=PORT)


if __name__ == "__main__":
    main()
